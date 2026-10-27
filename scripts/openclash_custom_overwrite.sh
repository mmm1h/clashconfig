#!/bin/sh
# OpenClash runs this after its own YAML rewriting and before firewall setup.
# Optional source/list paths let validation use isolated files.
set -eu

runtime_file=${1:?Missing OpenClash runtime config path}
source_file=${2:-$(uci -q get openclash.config.config_path)}
localnetwork_file=${3:-/etc/openclash/custom/openclash_custom_localnetwork_ipv4.list}

ruby -ryaml - "$runtime_file" "$source_file" "$localnetwork_file" <<'RUBY'
runtime_path, source_path, network_path = ARGV
abort 'OpenClash source and runtime paths must differ' if File.realpath(runtime_path) == File.realpath(source_path)

source = YAML.safe_load(File.read(source_path), aliases: true)
runtime = YAML.safe_load(File.read(runtime_path), aliases: true)
abort 'Source DNS configuration is missing' unless source['dns'].is_a?(Hash)
abort 'Source sniffer configuration is missing' unless source['sniffer'].is_a?(Hash)
listener = runtime.dig('dns', 'listen')
abort 'OpenClash DNS listener is missing' unless listener.is_a?(String) && !listener.empty?

# DNS policy and sniffing come from the imported YAML; OpenClash owns ports/UI.
runtime['dns'] = Marshal.load(Marshal.dump(source['dns']))
runtime['dns']['listen'] = listener
runtime['sniffer'] = Marshal.load(Marshal.dump(source['sniffer']))

# OpenClash installs the nftables marks and the route to utun itself.
# Running Mihomo auto-route/auto-redirect as well creates a second route owner.
if runtime['tun'].is_a?(Hash)
  runtime['tun']['auto-route'] = false
  runtime['tun']['auto-redirect'] = false
  runtime['tun']['auto-detect-interface'] = false
  runtime['tun']['strict-route'] = false
  runtime['tun'].delete('route-exclude-address-set')
  runtime['tun'].delete('route-exclude-address')
  runtime['tun']['dns-hijack'] = (runtime['tun'].fetch('dns-hijack', []) +
    source.dig('tun', 'dns-hijack').to_a).uniq
end

# Put fixed bypass ranges in OpenClash's native early-return set, so they also
# bypass its fwmark route. Preserve user entries outside the managed block.
first = '# --- mihomo.yaml TUN exclusions START (auto) ---'
last = '# --- mihomo.yaml TUN exclusions END (auto) ---'
lines = File.exist?(network_path) ? File.read(network_path).lines.map(&:chomp) : []
if lines.count(first) != lines.count(last) || lines.count(first) > 1 ||
   (lines.include?(first) && lines.index(first) >= lines.index(last))
  abort 'Malformed managed TUN exclusions block'
end
lines.slice!(lines.index(first)..lines.index(last)) if lines.include?(first)
def ipv4_network(value)
  return nil if value.is_a?(String) && value.include?(':')
  match = /\A(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?:\/(\d{1,2}))?\z/.match(value.to_s)
  abort 'Invalid IPv4 TUN exclusion' unless match
  octets = match.captures.first(4).map(&:to_i)
  prefix = match[5] ? match[5].to_i : 32
  abort 'Invalid IPv4 TUN exclusion' unless octets.all? { |x| x <= 255 } && prefix <= 32
  mask = (0xffffffff << (32 - prefix)) & 0xffffffff
  [octets.inject(0) { |ip, octet| (ip << 8) | octet } & mask, mask]
end

fake_net, fake_mask = ipv4_network(source.dig('dns', 'fake-ip-range') || '198.18.0.0/15')
abort 'An IPv4 Fake-IP range is required' unless fake_net
ranges = source.dig('tun', 'route-exclude-address').to_a.uniq.select do |value|
  address = ipv4_network(value)
  next false unless address
  network, mask = address
  if (network & fake_mask) == fake_net || (fake_net & mask) == network
    abort 'A TUN exclusion overlaps the Fake-IP range'
  end
  true
end
network_text = (lines + [first] + ranges + [last]).join("\n") + "\n"

def replace_file(path, contents, default_mode)
  return if File.exist?(path) && File.binread(path) == contents.b
  mode = File.exist?(path) ? File.stat(path).mode & 0o777 : default_mode
  temporary = File.join(File.dirname(path), ".openclash-#{Process.pid}-#{rand(1 << 30)}")
  File.open(temporary, File::WRONLY | File::CREAT | File::EXCL, mode) do |file|
    file.chmod(mode)
    file.write(contents)
    file.flush
    file.fsync
  end
  File.rename(temporary, path)
ensure
  File.unlink(temporary) if temporary && File.exist?(temporary)
end

replace_file(network_path, network_text, 0o644)
replace_file(runtime_path, YAML.dump(runtime), 0o600)
RUBY
