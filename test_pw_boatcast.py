import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 児島8RのBoatcastテキストURLへアクセス
        url = "https://race.boatcast.jp/txt/16/bc_oriten_20260304_16_08.txt"
        print(f"Navigating to {url} ...")
        
        # ネットワークのレスポンスを待つ
        response = await page.goto(url)
        print(f"Status: {response.status}")
        
        content = await page.content()
        # プレーンテキストの場合は body > pre に入ることが多い
        text = await page.evaluate("() => document.body.innerText")
        
        print("--- Content ---")
        print(text[:300])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
