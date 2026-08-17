import asyncio
import os
from playwright.async_api import async_playwright

# 配置信息
TARGET_URL = "https://zaobao-v2.hdilp.top/"
WIDTH = 720
HEIGHT = 960
SAVE_DIR = "screenshots"

async def capture_zaobao():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 增加 device_scale_factor 获取更清晰的截图
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            viewport={'width': WIDTH, 'height': HEIGHT},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )

        page = await context.new_page()

        print(f"正在访问: {TARGET_URL}...")
        # await page.goto(TARGET_URL, wait_until="networkidle")
        await page.goto(TARGET_URL)

        # 1. 等待加载屏幕消失
        print("等待初始化加载...")
        try:
            # 源码中加载完后 loading-screen 会加 .done
            await page.wait_for_selector(".loading-screen.done", state="attached", timeout=15000)
            # 额外等待 reveal-item 的进场动画完成
            await asyncio.sleep(2) 
        except:
            print("警告：未检测到加载完成标志，尝试继续...")

        page_index = 1

        while True:
            # 获取当前页码 (如 "1 / 3")
            label_el = await page.query_selector("#page-label")
            if not label_el:
                print("未找到页码标签，截取当前视口后退出。")
                await page.screenshot(path=f"{SAVE_DIR}/fallback_page.png")
                break

            current_page_text = await label_el.inner_text()
            print(f"当前页码: {current_page_text}")

            # 2. 截图当前页
            filename = f"zaobao_page_{page_index}.png"
            filepath = os.path.join(SAVE_DIR, filename)
            await page.screenshot(path=filepath)
            print(f"已保存: {filename}")

            # 3. 寻找“下一页”按钮
            next_btn = await page.query_selector("#page-next")
            if not next_btn:
                break

            # 4. 检查是否禁用 (源码中最后一页会添加 .disabled 类或 opacity 变低)
            is_disabled = await page.evaluate('''
                (btn) => {
                    return btn.classList.contains('disabled') || 
                           window.getComputedStyle(btn).pointerEvents === 'none' ||
                           window.getComputedStyle(btn).opacity < 0.5;
                }
            ''', next_btn)

            if is_disabled:
                print("已检测到最后一页。")
                break

            # 5. 点击翻页
            # 【核心修复】：使用 force=True 跳过稳定性检查，因为呼吸动画会导致元素永不稳定
            try:
                await next_btn.click(force=True)
            except Exception as e:
                print(f"点击失败: {e}")
                break

            # 6. 等待内容刷新（以 page-label 变化为准）
            try:
                # 等待文本内容变成不是当前的 current_page_text
                await page.wait_for_function(
                    f'document.getElementById("page-label").innerText !== "{current_page_text}"',
                    timeout=5000
                )
                # 给 0.5秒 让列表滑动动画/渲染完成
                await asyncio.sleep(0.5)
                page_index += 1
            except Exception:
                print("翻页后页面标签未更新，可能已到末尾。")
                break

        await browser.close()
        print(f"\n任务完成，保存在: {SAVE_DIR}")

if __name__ == "__main__":
    asyncio.run(capture_zaobao())
