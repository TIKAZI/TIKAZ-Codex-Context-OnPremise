import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

function valueFor(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || index + 1 >= process.argv.length) {
    throw new Error(`missing required argument: ${name}`);
  }
  return process.argv[index + 1];
}

const url = valueFor("--url");
const output = path.resolve(valueFor("--output"));
const moduleRoot = path.resolve(valueFor("--module-root"));
const playwrightUrl = pathToFileURL(path.join(moduleRoot, "playwright", "index.mjs")).href;
const { chromium } = await import(playwrightUrl);

await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
  const html = await page.content();
  await writeFile(path.join(output, "rendered.html"), html, "utf8");
  await page.screenshot({ path: path.join(output, "viewport.png"), fullPage: false });
  await writeFile(
    path.join(output, "metadata.json"),
    JSON.stringify(
      {
        requested_url: url,
        final_url: page.url(),
        title: await page.title(),
        status: response?.status() ?? null,
        captured_at: new Date().toISOString(),
        viewport: { width: 1440, height: 1000 },
      },
      null,
      2,
    ),
    "utf8",
  );
} finally {
  await browser.close();
}
