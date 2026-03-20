const axios = require('axios');
const cheerio = require('cheerio');

async function test() {
  console.log('开始测试百度搜索...');
  const url = 'https://www.baidu.com/s?wd=' + encodeURIComponent('今天科技新闻');
  const response = await axios.get(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
    },
    timeout: 10000
  });
  
  const $ = cheerio.load(response.data);
  const results = [];
  
  $('.c-container').each((i, el) => {
    if (i >= 3) return;
    const title = $(el).find('h3 a').text().trim();
    const url = $(el).find('h3 a').attr('href');
    const abstract = $(el).find('.c-abstract, .abstract').first().text().trim();
    results.push({title, url, abstract});
  });
  
  console.log('测试成功！找到' + results.length + '条结果:');
  console.log(JSON.stringify(results, null, 2));
}

test().catch(err => {
  console.error('错误:', err.message);
  process.exit(1);
});
