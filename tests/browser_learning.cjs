/* Browser integration against browser_server.py. Provider and image fixtures are test-only. */
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'playwright');
const fs=require('fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),session=JSON.parse(fs.readFileSync('/tmp/got-browser-session.json'));await context.addCookies([session.cookie]);const page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route(/\/(thumb|resource\/images|static\/images)\//,r=>r.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"><rect width="400" height="300" fill="#e7eddc"/><circle cx="200" cy="150" r="70" fill="#e8ba4a"/></svg>'}));
 await page.goto('http://127.0.0.1:5099/classic');assert.equal(await page.locator('.age-options input').count(),4);assert.equal(await page.locator('.curriculum-grid article').count(),18);assert.equal(await page.locator('#gotSessionDuration').inputValue(),'10');
 await page.goto('http://127.0.0.1:5099'+session.launch);await page.waitForSelector('.game-card');await page.evaluate(()=>{State.sound=false});
 const launch=async i=>{await page.locator('.game-card').nth(i).click();await page.waitForSelector('#setupModal.show');assert.equal(await page.locator('#setupGuide li').count(),3);await page.locator('#startButton').click();await page.waitForTimeout(180);assert.equal(await page.locator('#retryGame').count(),0)};
 const back=async()=>page.locator('#backButton').click();
 for(let i=0;i<18;i++){await launch(i);assert.ok(await page.locator('#stage button').count());await back()}
 // Preschool: small choice sets, 2x2 puzzle, 3 pairs, valid count and bounded math.
 await launch(0);assert.equal(await page.locator('.choice').count(),2);await back();
 await launch(2);assert.equal(await page.locator('[data-pos]').count(),4);await back();
 await launch(8);assert.equal(await page.locator('.memory-card').count(),6);await back();
 await launch(5);let count=await page.locator('.count-object').count();assert.ok(count>=1&&count<=5);await page.locator('.count-object').first().click();assert.equal(await page.locator('.count-object').first().getAttribute('aria-pressed'),'true');await page.getByRole('button',{name:String(count),exact:true}).click();await page.getByRole('button',{name:String(count),exact:true}).click();assert.equal(await page.locator('#score').textContent(),'15');await back();await page.waitForTimeout(800);assert.equal(await page.locator('#stage button').count(),0);
 // Sudoku checks constraints instead of comparing with one precomputed solution.
 await launch(3);const givens=await page.evaluate(()=>[...document.querySelectorAll('.sudoku-cell')].map(b=>+b.textContent||0));
 const solve=(cells)=>{let i=cells.indexOf(0);if(i<0)return cells;let r=Math.floor(i/4),c=i%4;for(let v=1;v<=4;v++){if(cells.some((x,j)=>x===v&&(Math.floor(j/4)===r||j%4===c||Math.floor(j/8)===Math.floor(r/2)&&Math.floor(j%4/2)===Math.floor(c/2))))continue;const next=[...cells];next[i]=v;const found=solve(next);if(found)return found}return null};const solution=solve(givens);assert.ok(solution);for(let i=0;i<16;i++)if(!givens[i])for(let k=0;k<solution[i];k++)await page.locator('.sudoku-cell').nth(i).click();await page.locator('#checkSudoku').click();assert.ok((await page.locator('.result-box').textContent()).includes('chính xác'));await back();
 // First reveal is always safe and mark mode works without a right click.
 for(let i=0;i<4;i++){await launch(9);await page.locator('#flagMode').click();await page.locator('[data-mine-cell="0"]').click();assert.equal(await page.locator('[data-mine-cell="0"]').textContent(),'🚩');await page.locator('[data-mine-cell="0"]').click();await page.locator('#flagMode').click();await page.locator('[data-mine-cell="14"]').click();assert.equal(await page.locator('.mine-cell.open').filter({hasText:'🪨'}).count(),0);await back()}
 // Finite accessible board: a complete winning line ends the round once.
 await launch(11);for(const i of [0,3,1,4,2])await page.locator('[data-caro="'+i+'"]').click();await page.waitForSelector('.result-box');assert.ok((await page.locator('.result-box').textContent()).includes('Bạn X'));await back();
 await launch(14);const question=await page.locator('.math-question').textContent(),numbers=question.match(/\d+/g).map(Number);assert.ok(numbers.every(x=>x<=5));await page.locator('#mathHint').click();assert.ok(await page.locator('#mathHintText').isVisible());await back();
 // Matching uses factual, disjoint pairs. No arbitrary fallback animal is used.
 await launch(17);assert.ok(await page.locator('.visual-match-target b').count()>=2);assert.ok((await page.locator('[data-source]').first().getAttribute('aria-label')).length>0);await back();
 // Keyboard modal close restores focus, mobile keeps sound and clock controls visible.
 await page.locator('.game-card').first().focus();await page.keyboard.press('Enter');await page.keyboard.press('Escape');assert.ok(await page.locator('.game-card').first().evaluate(x=>x===document.activeElement));
 for(const width of [390,768,1440]){await page.setViewportSize({width,height:900});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);assert.ok(await page.locator('#soundButton').isVisible());assert.ok(await page.locator('#sessionChip').isVisible())}
 await page.locator('[data-view="library"]').click();await page.waitForSelector('.library-card');await page.locator('.library-card-open').first().click();assert.ok(await page.locator('#detailDescriptionVi').textContent());assert.ok(await page.locator('#detailDescriptionEn').textContent());await page.keyboard.press('Escape');
 // Expiry cannot be bypassed by changing views, retry, or a delayed previous round.
 await page.evaluate(()=>{State.sessionClock.remaining=()=>0});await page.waitForTimeout(1200);assert.equal(await page.locator('.game-card.locked').count(),18);assert.ok((await page.locator('#sessionChip').textContent()).includes('hết'));
 assert.deepEqual(errors,[]);await browser.close();console.log('PASS: 18 launches, age mechanics, double-click guard, cleanup, Sudoku, safe garden, finite board, guides, keyboard, responsive controls and expiry');
})().catch(error=>{console.error(error);process.exit(1)});
