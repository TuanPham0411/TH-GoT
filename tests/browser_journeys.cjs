const {chromium}=require(process.env.PLAYWRIGHT_PATH||'playwright');
const fs=require('fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||undefined,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),fixture=JSON.parse(fs.readFileSync('/tmp/got-browser-session.json'));await context.addCookies([fixture.cookie]);
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const local=process.env.REALM_ASSET_MAP?JSON.parse(fs.readFileSync(process.env.REALM_ASSET_MAP)):{};
 await page.route('**/world-assets/*',r=>{const id=new URL(r.request().url()).pathname.split('/').pop();return local[id]?r.fulfill({path:local[id]}):r.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"><rect width="600" height="400" fill="#a7b7ab"/></svg>'});});
 await page.goto('http://127.0.0.1:5099/world');await page.locator('.subject-card').first().waitFor();
 const profiles=await page.locator('#journeyProfile option').evaluateAll(options=>options.map(o=>o.value));assert.equal(profiles.length,8);
 const titles=new Set();for(const id of profiles){await page.locator('#journeyProfile').selectOption(id);await page.waitForFunction(id=>document.querySelector('#worldProfile').value===id,id);titles.add(await page.locator('#journeyTitle').textContent());assert.equal(await page.locator('#journeyChapters li').count(),4);assert.ok((await page.locator('#stageFocus').textContent()).length>30);}
 assert.equal(titles.size,8);
 for(const width of [360,390,768,1440]){await page.setViewportSize({width,height:1000});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Overflow at '+width);}
 await page.setViewportSize({width:390,height:1000});await page.screenshot({path:'/tmp/got-grade-mobile.jpg',type:'jpeg',quality:65,fullPage:true});
 await page.setViewportSize({width:1440,height:1000});await page.locator('#journeyProfile').selectOption('grade-4');await page.locator('[data-region="stories"]').click();
 for(const [query,title,pages] of [['Tam Cam','Tấm Cám',8],['bac tuyet','Bạch Tuyết và bảy chú lùn',8],['Mai An Tiem','Mai An Tiêm',6],['lo lem','Cô bé Lọ Lem',6],['thanh giong','Thánh Gióng',6]]){
  await page.locator('#storySearch').fill(query);const card=page.locator('#worldStories article').first();assert.ok((await card.textContent()).includes(title));await card.getByRole('button').click();assert.equal(await page.locator('#storyContents option').count(),pages);await page.locator('#storyContents').selectOption(String(pages-1));assert.ok(await page.locator('.story-question').isVisible());await page.locator('[data-close="storyDialog"]').click();await card.getByRole('button').click();assert.equal(await page.locator('#storyContents').inputValue(),String(pages-1));await page.locator('[data-close="storyDialog"]').click();
 }
 const csrf=await page.locator('#world').getAttribute('data-csrf');
 async function session(profile){const result=await (await page.request.post('http://127.0.0.1:5099/api/sessions',{data:{csrf,profile,duration_minutes:10}})).json();return new URL(result.launch_url,'http://localhost').searchParams.get('session');}
 const token=await session('kindergarten-3');await page.goto('http://127.0.0.1:5099/world?session='+token);await page.waitForFunction(()=>document.querySelector('#journeyProfile').value==='kindergarten-3'&&document.querySelector('#journeyProfile').disabled);
 await page.locator('#continueJourney').click();assert.ok((await page.locator('#chapterSetup').textContent()).length>30);assert.ok(await page.locator('#chapterSteps button').nth(1).isDisabled());
 for(let step=0;step<2;step++){
  await page.locator('#chapterSteps button').nth(step).click();await page.getByRole('button',{name:'Bắt đầu thử thách',exact:true}).click();await page.locator('.round-options button').first().waitFor();const prompt=await page.locator('.round-prompt').textContent();const symbol=step===0?(prompt.includes('tròn')?'●':prompt.includes('vuông')?'■':'▲'):(prompt.includes('đỏ')?'🔴':prompt.includes('xanh lam')?'🔵':'🟡');await page.locator('.round-options').getByRole('button',{name:symbol,exact:true}).click();await page.getByRole('button',{name:'Tiếp tục chương →',exact:true}).click();
 }
 await page.getByRole('button',{name:'Mình đã làm và chia sẻ',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#chapterClosing').textContent.length>0);await page.locator('[data-close="journeyDialog"]').click();assert.match(await page.locator('#journeyProgress').textContent(),/1 \/ 4/);
 await page.reload();await page.waitForFunction(()=>document.querySelector('#journeyProgress').textContent.includes('1 / 4'));await page.screenshot({path:'/tmp/got-grade-journey.jpg',type:'jpeg',quality:65,fullPage:true});
 const older=await session('grade-5');await page.goto('http://127.0.0.1:5099/world?session='+older);await page.waitForFunction(()=>document.querySelector('#journeyProfile').value==='grade-5');await page.locator('#continueJourney').click();await page.locator('#chapterSteps button').first().click();await page.getByRole('button',{name:'Bắt đầu thử thách',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.round-prompt')?.textContent.includes('Cộng hai số đo'));assert.match(await page.locator('.round-prompt').textContent(),/\d+,\d{2}/);
 await page.locator('[data-close="learningDialog"]').click();await page.locator('#realmBag').click();await page.locator('#endWorldSession').click();await page.waitForFunction(()=>!document.querySelector('#journeyProfile').disabled);assert.equal((await page.request.get('http://127.0.0.1:5099/api/sessions/'+older)).status(),410);
 assert.deepEqual(errors,[]);await browser.close();console.log('PASS journeys: eight distinct tracks, 32 chapters, stage controls, story search/editions/bookmarks, four widths, verified chapter progression, reload persistence and Grade 5 decimal task');
})().catch(e=>{console.error(e);process.exit(1)});
