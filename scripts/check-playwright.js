const { chromium } = require("playwright");

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto("data:text/html,<title>ok</title><h1>Playwright OK</h1>");

  const title = await page.title();
  const heading = await page.locator("h1").textContent();

  await browser.close();

  if (title !== "ok" || heading !== "Playwright OK") {
    throw new Error(`Unexpected browser output: title=${title}, heading=${heading}`);
  }

  console.log("Playwright Chromium check passed.");
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exit(1);
});
