import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 通信をインターセプトしてURLとレスポンスをチェック
        async def handle_response(response):
            # jsonやapiを含むリクエストを対象にする
            if "api" in response.url or ".json" in response.url or "data" in response.url:
                try:
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        print(f"\\n--- Found JSON API: {response.url} ---")
                        data = await response.json()
                        # '展示' や 'タイム' に関連しそうなデータか簡易チェック
                        data_str = json.dumps(data, ensure_ascii=False)
                        if "time" in data_str.lower() or "展示" in data_str or "lap" in data_str.lower() or "turn" in data_str.lower():
                            print("🌟 Potential match found! Snippet:")
                            print(data_str[:500])
                        else:
                            print(f"Data received (size: {len(data_str)})")
                except Exception as e:
                    pass
        
        page.on("response", handle_response)
        
        print("Navigation to https://race.boatcast.jp/?jo=16 ...")
        await page.goto("https://race.boatcast.jp/?jo=16", wait_until="networkidle")
        
        # 画面に描画されたテキストも少し確認（データが表示されるまで待つ）
        await page.wait_for_timeout(3000)
        content = await page.content()
        if "タイム" in content or "展示" in content:
            print("\\n✅ ページ上にデータが描画されました")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
