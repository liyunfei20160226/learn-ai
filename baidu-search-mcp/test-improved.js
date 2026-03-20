const axios = require('axios');
const cheerio = require('cheerio');

async function test() {
  console.log('测试改进后的百度搜索...');
  const url = 'https://www.baidu.com/s?wd=' + encodeURIComponent('人工智能 最新进展');
  const response = await axios.get(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
    },
    timeout: 10000
  });
  
  const $ = cheerio.load(response.data);
  const results = [];
  
  $(".c-container").each((index, element) => {
    if (results.length >= 5) return;

    const $el = $(element);
    const $title = $el.find("h3 a, .t a");
    let abstract = "";

    const abstractSelectors = [
      ".c-abstract",
      ".abstract",
      ".content-right_1VRdl p",
      ".c-span18 p",
      "p",
      ".result-abstract",
      ".mu"
    ];

    for (const selector of abstractSelectors) {
      const $abs = $el.find(selector);
      if ($abs.length > 0) {
        abstract = $abs.first().text().trim();
        if (abstract) break;
      }
    }

    const title = $title.text().trim();
    let url = $title.attr("href") || "";

    if (!title || !url) return;

    results.push({title, url, abstract});
  });
  
  console.log('测试成功！找到' + results.length + '条结果:');
  console.log(JSON.stringify(results, null, 2));
}

test().catch(err => {
  console.error('错误:', err.message);
  process.exit(1);
});
