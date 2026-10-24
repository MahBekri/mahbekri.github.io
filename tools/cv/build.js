// Builds the CVs with the site's fonts: node tools/cv/build.js
// cv.html -> cv.pdf (English), cv-fr.html -> cv-fr.pdf (French)
const { chromium } = require('playwright');
const path = require('path');
const JOBS = [['cv.html', 'cv.pdf'], ['cv-fr.html', 'cv-fr.pdf']];
(async () => {
  const b = await chromium.launch();
  for (const [src, out] of JOBS) {
    const p = await b.newPage();
    await p.goto('file://' + path.join(__dirname, src));
    await p.evaluate(() => document.fonts.ready);
    await p.pdf({ path: path.join(__dirname, '..', '..', out), format: 'A4', preferCSSPageSize: true, printBackground: true,
      displayHeaderFooter: true, headerTemplate: '<span></span>',
      footerTemplate: '<div style="width:100%;font:7.5pt Segoe UI,Helvetica,Arial,sans-serif;color:#586378;padding:0 17mm;display:flex;justify-content:space-between"><span>Mahmoud Bekri · Curriculum vitae</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>' });
    await p.close();
  }
  await b.close();
})();
