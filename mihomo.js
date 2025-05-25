function main(config) {
  // Ensure basic structure exists (though assignments below might overwrite)
  if (!config['proxy-groups']) {
    config['proxy-groups'] = [];
  }
  if (!config['rule-providers']) {
    config['rule-providers'] = {};
  }
  if (!config['rules']) {
    config['rules'] = [];
  }

  // Populate proxy-groups from the YAML configuration
  config["proxy-groups"] = [
    {
      name: "🚀 节点选择",
      type: "select",
      proxies: [
        "♻️ 自动选择",
        "DIRECT",
        "🇭🇰 香港",
        "🇨🇳 台湾",
        "🇸🇬 新加",
        "🇯🇵 日本",
        "🇺🇲 美国",
        "🍉 其他地区"
      ]
    },
    {
      name: "♻️ 自动选择",
      type: "url-test",
      url: "http://www.gstatic.com/generate_204",
      interval: 300,
      tolerance: 50,
      "include-all": true,
      filter: "(?=.*(港|HK|Hong Kong|🇭🇰|HongKong))^((?!(2X|4X)).)*$"
      // proxies: [] // Implies filtering from all available proxies
    },
    {
      name: "🎥 油管奈飞",
      type: "select",
      proxies: [
        "♻️ 自动选择",
        "🚀 节点选择",
        "🍉 其他地区",
        "🇸🇬 新加",
        "🇭🇰 香港",
        "🇨🇳 台湾",
        "🇯🇵 日本",
        "🇺🇲 美国"
      ]
    },
    {
      name: "📺 哔哩哔哩",
      type: "select",
      proxies: [
        "🎯 全球直连", // This group should exist or map to DIRECT
        "🇨🇳 台湾",
        "🇭🇰 香港"
      ]
    },
    {
      name: "🍎 苹果服务",
      type: "select",
      proxies: [
        "DIRECT",
        "🚀 节点选择",
        "🇺🇲 美国",
        "🇭🇰 香港",
        "🇨🇳 台湾",
        "🇸🇬 新加",
        "🇯🇵 日本"
      ]
    },
    {
      name: "🎮 游戏平台",
      type: "select",
      proxies: [
        "DIRECT",
        "🚀 节点选择",
        "🍉 其他地区",
        "🇺🇲 美国",
        "🇭🇰 香港",
        "🇨🇳 台湾",
        "🇸🇬 新加",
        "🇯🇵 日本"
      ]
    },
    {
      name: "⚽ 游戏下载",
      type: "select",
      proxies: [
        "DIRECT",
        "🚀 节点选择",
        "🍉 其他地区"
      ]
    },
    {
      name: "Ⓜ️ 微软服务",
      type: "select",
      proxies: [
        "DIRECT",
        "🚀 节点选择",
        "🍉 其他地区"
      ]
    },
    {
      name: "🥦 OPENAI",
      type: "url-test",
      url: "https://api.openai.com/v1/completions",
      interval: 300,
      tolerance: 100,
      "include-all": true,
      filter: "(?=.*(gpt|GPT))^((?!(4X)).)*$"
      // proxies: [] // Implies filtering from all available proxies
    },
    {
      name: "🎯 全球直连",
      type: "select",
      proxies: [
        "DIRECT"
        // "🚀 节点选择", // Optionally add other fallbacks if DIRECT is not primary
        // "🍉 其他地区"
      ]
    },
    {
      name: "💩 ‍广告屏蔽",
      type: "select",
      proxies: [
        "REJECT",
        "DIRECT"
        // "🚀 节点选择" // Optional
      ]
    },
    {
      name: "🐟 未知网站",
      type: "select",
      proxies: [
        "DIRECT",
        "♻️ 自动选择",
        "🚀 节点选择",
        "🍉 其他地区",
        "🇭🇰 香港",
        "🇨🇳 台湾",
        "🇸🇬 新加",
        "🇯🇵 日本",
        "🇺🇲 美国"
      ]
    },
    {
      name: "🇭🇰 香港",
      type: "select", // Per INI, this was a select group with a filter
      "include-all": true,
      filter: "(?=.*(港|HK|Hong Kong|🇭🇰|HongKong))^((?!(2X|4X)).)*$"
      // proxies: [] // populated by proxies matching the filter from all available
    },
    {
      name: "🇯🇵 日本",
      type: "url-test",
      url: "http://www.gstatic.com/generate_204",
      interval: 300,
      tolerance: 50,
      "include-all": true,
      filter: "(?=.*(日本|川日|东京|大阪|泉日|埼玉|沪日|深日|[^-]日|JP|Japan))^((?!(2X|4X)).)*$"
      // proxies: []
    },
    {
      name: "🇺🇲 美国",
      type: "url-test",
      url: "http://www.gstatic.com/generate_204",
      interval: 300,
      tolerance: 50,
      "include-all": true,
      filter: "(?=.*(美|US|United States))^((?!(2X|4X)).)*$"
      // proxies: []
    },
    {
      name: "🇸🇬 新加",
      type: "url-test",
      url: "http://www.gstatic.com/generate_204",
      interval: 300,
      tolerance: 50,
      "include-all": true,
      filter: "(?=.*(新加坡|坡|狮城|SG|Singapore))^((?!(2X|4X)).)*$"
      // proxies: []
    },
    {
      name: "🇨🇳 台湾",
      type: "url-test",
      url: "http://www.gstatic.com/generate_204",
      interval: 300,
      tolerance: 50,
      "include-all": true,
      filter: "(台|新北|彰化|TW|Taiwan)"
      // proxies: []
    },
    {
      name: "🍉 其他地区",
      type: "select", // Per INI, this was a select group with a filter
      "include-all": true,
      filter: "^(?!.*?(?:港|HK|🇭🇰|日本|JP|美|US|新加坡|坡|SG|台|新北|彰化|TW)).+$"
      // proxies: [] // populated by proxies matching the filter from all available
    }
  ];

  // Populate rule-providers from the YAML configuration
  const myRuleProviders = {
    "mmm1h_Direct": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/mmm1h/clashconfig/main/rules/Direct.list",
      path: "./ruleset/mmm1h_Direct.yaml", // Local cache path
      interval: 86400,
      format: "text"
    },
    "mmm1h_GameDownload": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/mmm1h/clashconfig/main/rules/GameDownload.list",
      path: "./ruleset/mmm1h_GameDownload.yaml",
      interval: 86400,
      format: "text"
    },
    "mmm1h_US": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/mmm1h/clashconfig/main/rules/US.list",
      path: "./ruleset/mmm1h_US.yaml",
      interval: 86400,
      format: "text"
    },
    "mmm1h_JP": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/mmm1h/clashconfig/refs/heads/main/rules/JP.list",
      path: "./ruleset/mmm1h_JP.yaml",
      interval: 86400,
      format: "text"
    },
    "mmm1h_Rules": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/mmm1h/clashconfig/main/rules/Rules.list",
      path: "./ruleset/mmm1h_Rules.yaml",
      interval: 86400,
      format: "text"
    },
    "blackmatrix7_WeChat": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Clash/WeChat/WeChat.list",
      path: "./ruleset/blackmatrix7_WeChat.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_LocalAreaNetwork": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/LocalAreaNetwork.list",
      path: "./ruleset/ACL4SSR_LocalAreaNetwork.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_UnBan": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/UnBan.list",
      path: "./ruleset/ACL4SSR_UnBan.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_NetEaseMusic": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/NetEaseMusic.list",
      path: "./ruleset/ACL4SSR_NetEaseMusic.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_GoogleFCM": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/GoogleFCM.list",
      path: "./ruleset/ACL4SSR_GoogleFCM.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_GoogleCN": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/GoogleCN.list",
      path: "./ruleset/ACL4SSR_GoogleCN.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_SteamCN": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/SteamCN.list",
      path: "./ruleset/ACL4SSR_SteamCN.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_OneDrive": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/OneDrive.list",
      path: "./ruleset/ACL4SSR_OneDrive.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_ChinaMedia": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/ChinaMedia.list",
      path: "./ruleset/ACL4SSR_ChinaMedia.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Microsoft": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Microsoft.list",
      path: "./ruleset/ACL4SSR_Microsoft.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_OpenAi": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/OpenAi.list",
      path: "./ruleset/ACL4SSR_OpenAi.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_AI": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/AI.list",
      path: "./ruleset/ACL4SSR_AI.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_BanAD": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanAD.list",
      path: "./ruleset/ACL4SSR_BanAD.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_BanProgramAD": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanProgramAD.list",
      path: "./ruleset/ACL4SSR_BanProgramAD.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_BanEasyList": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyList.list",
      path: "./ruleset/ACL4SSR_BanEasyList.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_BanEasyListChina": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/BanEasyListChina.list",
      path: "./ruleset/ACL4SSR_BanEasyListChina.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Apple": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Apple.list",
      path: "./ruleset/ACL4SSR_Apple.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Epic": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/Epic.list",
      path: "./ruleset/ACL4SSR_Epic.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Origin": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/Origin.list",
      path: "./ruleset/ACL4SSR_Origin.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Sony": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/Sony.list",
      path: "./ruleset/ACL4SSR_Sony.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Steam": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/Steam.list",
      path: "./ruleset/ACL4SSR_Steam.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Nintendo": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/Nintendo.list",
      path: "./ruleset/ACL4SSR_Nintendo.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_YouTube": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/YouTube.list",
      path: "./ruleset/ACL4SSR_YouTube.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Netflix": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/Netflix.list",
      path: "./ruleset/ACL4SSR_Netflix.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_AmazonIp": {
      type: "http",
      behavior: "classical", // Or "ipcidr" if the list is purely IPs
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/AmazonIp.list",
      path: "./ruleset/ACL4SSR_AmazonIp.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Bahamut": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/Bahamut.list",
      path: "./ruleset/ACL4SSR_Bahamut.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_BilibiliHMT": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/BilibiliHMT.list",
      path: "./ruleset/ACL4SSR_BilibiliHMT.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Bilibili": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/Bilibili.list",
      path: "./ruleset/ACL4SSR_Bilibili.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_ProxyMedia": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/ProxyMedia.list",
      path: "./ruleset/ACL4SSR_ProxyMedia.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_ProxyGFWlist": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/ProxyGFWlist.list",
      path: "./ruleset/ACL4SSR_ProxyGFWlist.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Telegram": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Telegram.list",
      path: "./ruleset/ACL4SSR_Telegram.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_ChinaDomain": {
      type: "http",
      behavior: "classical", // Or "domain"
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/ChinaDomain.list",
      path: "./ruleset/ACL4SSR_ChinaDomain.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_ChinaCompanyIp": {
      type: "http",
      behavior: "classical", // Or "ipcidr"
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/ChinaCompanyIp.list",
      path: "./ruleset/ACL4SSR_ChinaCompanyIp.yaml",
      interval: 86400,
      format: "text"
    },
    "ACL4SSR_Download": {
      type: "http",
      behavior: "classical",
      url: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Download.list",
      path: "./ruleset/ACL4SSR_Download.yaml",
      interval: 86400,
      format: "text"
    }
  };
  config["rule-providers"] = Object.assign(config["rule-providers"], myRuleProviders);

  // Populate rules from the YAML configuration
  config["rules"] = [
    // ;自定义规则
    "RULE-SET,mmm1h_Direct,🎯 全球直连",
    "RULE-SET,mmm1h_GameDownload,⚽ 游戏下载",
    "RULE-SET,mmm1h_US,🇺🇲 美国",
    "RULE-SET,mmm1h_JP,🇯🇵 日本",
    "RULE-SET,mmm1h_Rules,🚀 节点选择",

    // ;直连规则 & 分流规则 (Order from INI)
    "RULE-SET,blackmatrix7_WeChat,🎯 全球直连",
    "RULE-SET,ACL4SSR_LocalAreaNetwork,🎯 全球直连",
    "RULE-SET,ACL4SSR_UnBan,🎯 全球直连",
    "RULE-SET,ACL4SSR_NetEaseMusic,🎯 全球直连",
    "RULE-SET,ACL4SSR_GoogleFCM,🎯 全球直连",
    "RULE-SET,ACL4SSR_GoogleCN,🎯 全球直连",
    "RULE-SET,ACL4SSR_SteamCN,🎯 全球直连",
    "RULE-SET,ACL4SSR_OneDrive,🎯 全球直连",
    "RULE-SET,ACL4SSR_ChinaMedia,🎯 全球直连",
    "RULE-SET,ACL4SSR_Microsoft,Ⓜ️ 微软服务",
    "RULE-SET,ACL4SSR_OpenAi,🥦 OPENAI",
    "RULE-SET,ACL4SSR_AI,🥦 OPENAI",
    "RULE-SET,ACL4SSR_BanAD,💩 ‍广告屏蔽",
    "RULE-SET,ACL4SSR_BanProgramAD,💩 ‍广告屏蔽",
    "RULE-SET,ACL4SSR_BanEasyList,💩 ‍广告屏蔽",
    "RULE-SET,ACL4SSR_BanEasyListChina,💩 ‍广告屏蔽",
    "RULE-SET,ACL4SSR_Apple,🍎 苹果服务",
    "RULE-SET,ACL4SSR_Epic,🎮 游戏平台",
    "RULE-SET,ACL4SSR_Origin,🎮 游戏平台",
    "RULE-SET,ACL4SSR_Sony,🎮 游戏平台",
    "RULE-SET,ACL4SSR_Steam,🎮 游戏平台",
    "RULE-SET,ACL4SSR_Nintendo,🎮 游戏平台",
    "RULE-SET,ACL4SSR_YouTube,🎥 油管奈飞",
    "RULE-SET,ACL4SSR_Netflix,🎥 油管奈飞",
    "RULE-SET,ACL4SSR_AmazonIp,🎥 油管奈飞",
    "RULE-SET,ACL4SSR_Bahamut,🇨🇳 台湾",
    "RULE-SET,ACL4SSR_BilibiliHMT,📺 哔哩哔哩",
    "RULE-SET,ACL4SSR_Bilibili,📺 哔哩哔哩",
    "RULE-SET,ACL4SSR_ProxyMedia,🚀 节点选择",
    "RULE-SET,ACL4SSR_ProxyGFWlist,🚀 节点选择",
    "RULE-SET,ACL4SSR_Telegram,🚀 节点选择",

    // ;中国大陆IP和域名直连
    "RULE-SET,ACL4SSR_ChinaDomain,🎯 全球直连",
    "RULE-SET,ACL4SSR_ChinaCompanyIp,🎯 全球直连",
    "RULE-SET,ACL4SSR_Download,🎯 全球直连",

    // ;局域网和中国大陆IP直连 (GEOIP,CN)
    "GEOIP,CN,🎯 全球直连",

    // ;未知网站 (兜底规则)
    "MATCH,🐟 未知网站"
  ];

  return config;
}
