#!/usr/bin/env node
const fs = require('fs');
const puppeteer = require('puppeteer');
const { spawn } = require('child_process');

// Usage: node render_multi_lottie.js <output.apng> <layer1.json> <layer2.json> ...
async function main() {
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.error('Usage: render_multi_lottie.js <output.apng> <layer1.json> [layer2.json ...]');
        process.exit(1);
    }
    const output = args[0];
    const jsonPaths = args.slice(1);

    const lottiePath = require.resolve('lottie-web/build/player/lottie.min.js');
    const lottieJs = fs.readFileSync(lottiePath, 'utf8');
    const layersData = jsonPaths.map(p => fs.readFileSync(p, 'utf8'));

    const html = `
    <!DOCTYPE html>
    <html>
    <head>
    <script>${lottieJs}</script>
    <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: transparent; overflow: hidden; width: 512px; height: 512px; }
    #container { position: relative; width: 512px; height: 512px; }
    .layer { position: absolute; left: 0; top: 0; width: 512px; height: 512px; }
    </style>
    </head>
    <body>
    <div id="container">
      ${layersData.map((_, i) => `<div class="layer" id="layer_${i}"></div>`).join('\n')}
    </div>
    <script>
    const datas = [${layersData.join(',')}];
    window.anims = datas.map((d, i) => lottie.loadAnimation({
        container: document.getElementById('layer_' + i),
        renderer: 'svg',
        loop: false,
        autoplay: false,
        animationData: d
    }));
    window.goToFrame = function(f) {
        window.anims.forEach(a => {
            const total = Math.max(1, Math.round(a.totalFrames));
            const clamped = Math.min(Math.max(0, f), total - 1);
            a.goToAndStop(clamped, true);
        });
    };
    </script>
    </body>
    </html>
    `;

    const browser = await puppeteer.launch({
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    });
    const page = await browser.newPage();
    await page.setViewport({ width: 512, height: 512 });
    await page.setContent(html);
    await new Promise(r => setTimeout(r, 400));

    const numFrames = 180;
    const fps = 60;
    const ffmpegArgs = [
        '-v', 'error', '-y',
        '-f', 'image2pipe', '-c:v', 'png', '-r', String(fps), '-i', '-',
        '-plays', '1',
        '-frames:v', String(numFrames),
        '-an', output
    ];
    const ffmpeg = spawn('ffmpeg', ffmpegArgs);
    const ffmpegStdin = ffmpeg.stdin;
    const container = await page.$('#container');

    for (let f = 0; f < numFrames; f++) {
        await page.evaluate(frame => window.goToFrame(frame), f);
        const screenshot = await container.screenshot({ omitBackground: true, type: 'png' });
        if (!ffmpegStdin.write(screenshot)) {
            await new Promise(resolve => ffmpegStdin.once('drain', resolve));
        }
    }
    ffmpegStdin.end();
    await new Promise((resolve, reject) => {
        ffmpeg.on('exit', code => code === 0 ? resolve() : reject(new Error('ffmpeg exit code ' + code)));
    });
    await browser.close();
    console.log(`Saved composite animation to ${output}`);
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
