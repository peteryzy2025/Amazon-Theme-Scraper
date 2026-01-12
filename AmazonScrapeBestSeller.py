from datetime import datetime
import time
import psycopg2
from DrissionPage import ChromiumPage
from openai import OpenAI

DB_HOST = "192.168.110.54"
DB_PORT = "5432"
DB_NAME = "overlord_db"
DB_USER = "user1"
DB_PASS = "user555Y1"

OPENAI_API_KEY = "sk-d84933834d374be9a7d814d79cbcad6e"
OPENAI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
OPENAI_MODEL = "qwen-plus"

BEST_SELLER_START_URL = "https://www.amazon.com/s?k=Shirt&i=fashion-novelty&s=exact-aware-popularity-rank&crid=YLBANN75IKXD&qid=1767339117&sprefix=shirt%2Cfashion-novelty%2C462&xpid=BnGJNx0oBq0gz&ref=sr_st_exact-aware-popularity-rank&ds=v1%3AbGTG%2BvBKF3pkdWNuMKjeKqkR0rIwAXLQF%2BFxvBE96BY"


class DatabaseManager:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
        )
        self.cursor = self.conn.cursor()

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def commit(self):
        self.conn.commit()

    def record_exists(self, asin, crawl_date):
        query = """
        SELECT EXISTS(
            SELECT 1
            FROM product_rank_history
            WHERE product_id = %s
            AND crawl_date = %s
        )
        """
        self.cursor.execute(query, (asin, crawl_date))
        return self.cursor.fetchone()[0]

    def product_exists(self, asin):
        query = """
        SELECT EXISTS(
            SELECT 1
            FROM amazon_product
            WHERE asin = %s
        )
        """
        self.cursor.execute(query, (asin,))
        return self.cursor.fetchone()[0]

    def insert_amazon_product(
        self,
        asin,
        title,
        title_translation,
        subject,
        subject_translation,
        image_url,
        launch_date,
        crawl_at,
        product_type,
    ):
        query = """
        INSERT INTO amazon_product (
            asin, title, title_translation, subject, subject_translation,
            image_url, launch_date, created_at, product_type, is_latest_deal, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'f', %s)
        RETURNING asin
        """
        self.cursor.execute(
            query,
            (
                asin,
                title,
                title_translation,
                subject,
                subject_translation,
                image_url,
                launch_date,
                crawl_at,
                product_type,
                crawl_at,
            ),
        )
        return self.cursor.fetchone()[0]

    def insert_product_rank_history(self, asin, crawl_date, rank, rank_category, crawl_at):
        query = """
        INSERT INTO product_rank_history (crawl_date, rank, rank_category, crawled_at, product_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING crawl_date, product_id
        """
        self.cursor.execute(query, (crawl_date, rank, rank_category, crawl_at, asin))
        return self.cursor.fetchone()


class ContentProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

    def _call_openai(self, messages):
        try:
            response = self.client.chat.completions.create(model=OPENAI_MODEL, messages=messages)
            content = response.choices[0].message.content
            return content.replace("'", "''")
        except Exception as e:
            print(f"API调用出错: {e}")
            return "识别失败"

    def recognize_text_from_title(self, title):
        prompt = f""""Please extract the core thematic phrase from the product title following these rules:
                            1. **Structural Analysis**:
                            - Focus on phrases near product terms but exclude the product word itself
                            - Ignore product types (Hat/Cap), audiences (Men/Women), colors, materials,specifications and printing-related terms(Print/Printing)
                            2. **Cultural/Linguistic Features**:
                            - Preserve complete emotional expressions or humorous phrases
                            - Maintain cultural references/puns in their original phrase structures
                            3. **Selection Criteria**:
                            - When multiple candidates exist:
                            a) Choose longer phrases
                            b) Prioritize semantically concrete/complete expressions
                            c) Prefer complete sentence segments
                            4. **Final Validation**:
                            - Remove any remaining product terms before output
                            Examples:
                            Title: The Sao Tome and Principe Flag and Freedom Baseball Cap for Men Women Adjustable Breathable Mesh Trucker Hat Unisex
                            Extract: The Sao Tome and Principe Flag and Freedom

                            Title: Nufar I Don't Need Therapy I Have My Sister 11oz Fun Coffee Mugs Novelty Ceramics Cup
                            Extract: I Don't Need Therapy I Have My Sister
                            Now process this title: {title}
                            Output only the final English phrase without explanations"""
        messages = [{"role": "user", "content": prompt}]
        return self._call_openai(messages)

    def translate_subject(self, subject):
        prompt = f""""# 角色设定
你是一位专业的亚马逊电商运营专家，专门负责产品主题标签的本地化翻译。

# 任务说明
请将以下亚马逊产品主题标签/关键词从英文翻译成中文。这些通常是：
- 产品主题标签（如节日、季节、活动主题）
- 产品风格关键词
- 目标人群标签
- 使用场景标签

# 翻译原则

## 核心要求：
1. **保持简洁**：中文表达要简短有力，控制在3-10个字
2. **准确传达主题**：完整表达原文的主题概念
3. **符合中文标签习惯**：使用中文用户熟悉的表达方式
4. **保留关键信息**：不丢失任何重要的主题元素

## 具体规则：

### A. 节日/季节主题：
- 准确翻译节日名称
- 保留节日氛围
- 符合中文节日表达习惯
- 例如：Valentine's Day → 情人节主题

### B. 情感/风格主题：
- 准确传达情感色彩
- 使用地道中文表达
- 保持风格一致性
- 例如：Romantic Love → 浪漫爱情

### C. 事件/活动主题：
- 准确翻译事件名称
- 保留事件特殊性
- 添加"主题"或"风格"后缀（如适用）
- 例如：Super Bowl → 超级碗主题

### D. 人群/场景主题：
- 准确描述目标人群
- 清晰表达使用场景
- 使用市场常用术语

## 翻译示例参考：

### 输入示例：
1. "Christmas Family Reunion Theme"
2. "Beach Summer Vacation Style"
3. "Gamer RGB Lighting Setup"
4. "Office Professional Business"

### 输出示例：
1. "圣诞家庭团圆主题"
2. "海滩夏日度假风"
3. "游戏玩家RGB光效"
4. "办公商务专业款"

## 特别注意：
1. **专有名词处理**：
   - 球队名、赛事名：保留核心意思，简短翻译
   - 地名：标准中文译名
   - 品牌名：一般不翻译

2. **文化适配**：
   - 西方节日要准确但符合中文习惯
   - 体育赛事用中国用户熟悉的表达
   - 避免直译造成的生硬感

3. **格式要求**：
   - 每行一个翻译结果
   - 不加引号
   - 不加解释说明
   - 保持原始顺序
   - 不要出现英文
   - 不要出现如 "\\n" 等特殊字符

## 待翻译的主题标签：
{subject}

## 请开始翻译："""
        messages = [{"role": "user", "content": prompt}]
        result = self._call_openai(messages)
        return result.replace("\n", "")

    def translate_title(self, title):
        prompt = f"""# 角色设定
你是一名经验丰富的亚马逊跨境电商运营专家，专门负责产品标题的本地化翻译。

# 任务说明
请将以下亚马逊产品标题从英文翻译成中文。这些标题通常包含：
1. 产品类型（T-Shirt, Hoodie, Dress等）
2. 目标人群（Women's, Men's, Kids, Baby等）
3. 设计主题/图案
4. 产品特性（材质、款式、尺寸等）
5. 品牌/授权信息

# 翻译原则

## 核心要求：
1. **信息完整性**：保留原文所有关键信息
2. **准确性第一**：技术规格、尺寸、材质必须100%准确
3. **符合中文标题结构**：使用"人群+主题+特性+产品类型"结构
4. **可读性强**：中文表达自然流畅，符合电商标题习惯

# 格式要求：
1. 不加引号
2. 直接输出中文标题

# 待翻译标题：
{title}

# 中文标题："""
        messages = [{"role": "user", "content": prompt}]
        result = self._call_openai(messages)
        return result.replace("\n", "")


class AmazonScraper:
    def __init__(self, db_manager, content_processor):
        self.driver = ChromiumPage()
        self.db = db_manager
        self.processor = content_processor
        self.title_list = []

    def get_items_index_list(self, list_selector):
        data_index_list = []
        item_outer_blocks = self.driver.eles(list_selector)
        for item_outer_block in item_outer_blocks:
            data_index = item_outer_block.attr("data-index")
            if data_index is None:
                continue
            data_index = str(data_index).strip()
            if not data_index:
                continue
            data_index_list.append(data_index)
        return data_index_list

    def get_exact_item_xpath(self, index):
        return f'xpath://span[@class="rush-component s-latency-cf-section"]//div[@role="listitem" and @data-index="{index}"]'

    def get_title(self, index):
        title_xpath = self.get_exact_item_xpath(index) + "//a//h2"
        title = self.driver.ele(title_xpath)
        title = title.texts()[0]
        return title.replace("'", "''")

    def get_picture(self, index):
        picture_xpath = self.get_exact_item_xpath(index) + "//img"
        picture = self.driver.ele(picture_xpath)
        return picture.attr("src")

    def get_ASIN(self, index):
        ASIN_xpath = (
            self.get_exact_item_xpath(index)
            + '//span[@class="word-title" and text()="ASIN:"]//following-sibling::span[@class="font-weight-b"]'
        )
        ASIN = self.driver.ele(ASIN_xpath)
        return ASIN.texts()[0].strip()

    def get_launch_date(self, index):
        try:
            launch_date_xpath = self.get_exact_item_xpath(index) + '//span[@class="mr-ext-1 mt-ext-3"]'
            launch_date_info = self.driver.ele(launch_date_xpath)
            launch_date_info = launch_date_info.texts()[1]
            launch_date = launch_date_info.split("(")[0].replace(" ", "")
            launched_time = launch_date_info.split("(")[1].split(")")[0]
            return str(launch_date), str(launched_time)
        except:
            return None, None

    def get_item_rank(self, index):
        try:
            rank_xpath = self.get_exact_item_xpath(index) + '//span[@class="font-weight-b"]/span[contains(@class,"rank-box")]'
            rank = self.driver.eles(rank_xpath)[0].texts()[0]
            rank = rank.replace("#", "").replace(",", "")
            return int(rank)
        except:
            return None

    def get_item_rank_category(self, index):
        try:
            rank_category_xpath = self.get_exact_item_xpath(index) + '//p[@class="bsr-list-item"][1]/span[contains(@class,"exts-color-blue")]'
            rank_category = self.driver.eles(rank_category_xpath)[0].texts()[0]
            return rank_category
        except:
            return None

    def get_current_page_number(self):
        try:
            ele = self.driver.ele(
                'xpath://span[contains(@class,"s-pagination-item") and contains(@class,"s-pagination-selected")]',
                timeout=2,
            )
            if not ele:
                return None
            text = None
            try:
                texts = ele.texts()
                text = texts[0] if texts else None
            except Exception:
                text = getattr(ele, "text", None)
            if not text:
                return None
            return int(str(text).strip())
        except Exception:
            return None

    def next_page(self):
        try:
            btn = self.driver.ele('xpath://a[contains(@class,"s-pagination-next")]', timeout=5)
            if not btn:
                print("Error clicking next page: next button not found")
                return False
            btn.click()
            return True
        except Exception as e:
            print(f"Error clicking next page: {e}")
            return False

    def days_to_int(self, days_str):
        try:
            return int(days_str.replace(",", ""))
        except:
            return 0

    def created_time(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def process_item(self, data_index, product_type):
        crawl_at = self.created_time()
        crawl_date = crawl_at.split(" ")[0]
        ASIN = self.get_ASIN(data_index)

        if self.db.record_exists(ASIN, crawl_date):
            product_exists = self.db.product_exists(ASIN)
            if product_exists:
                print(f"[{crawl_at}][SKIP][BOTH_EXIST] asin={ASIN} crawl_date={crawl_date}")
            else:
                print(f"[{crawl_at}][SKIP][HISTORY_EXIST] asin={ASIN} crawl_date={crawl_date}")
            return

        product_exists = self.db.product_exists(ASIN)

        if product_exists:
            rank = self.get_item_rank(data_index)
            rank_category = self.get_item_rank_category(data_index)

            print(
                f"[{crawl_at}][INSERT][HISTORY_ONLY] table=product_rank_history asin={ASIN} crawl_date={crawl_date} rank={rank} rank_category={rank_category}"
            )

            try:
                self.db.insert_product_rank_history(ASIN, crawl_date, rank, rank_category, crawl_at)
                self.db.commit()
                print(f"[{crawl_at}][OK][HISTORY_ONLY] inserted=product_rank_history asin={ASIN} crawl_date={crawl_date}")
                if not self.db.record_exists(ASIN, crawl_date):
                    print(
                        f"[{crawl_at}][WARN][NOT_FOUND_AFTER_COMMIT] table=product_rank_history asin={ASIN} crawl_date={crawl_date}"
                    )
            except Exception as e:
                print(
                    f"[{crawl_at}][FAIL][HISTORY_ONLY] insert_failed=product_rank_history asin={ASIN} crawl_date={crawl_date} err={e}"
                )
                self.db.conn.rollback()
            return

        title = self.get_title(data_index)
        title_translation = self.processor.translate_title(title)
        subject = self.processor.recognize_text_from_title(title)
        subject_translation = self.processor.translate_subject(subject)
        image_url = self.get_picture(data_index)
        launch_date, launched_time = self.get_launch_date(data_index)
        rank = self.get_item_rank(data_index)
        rank_category = self.get_item_rank_category(data_index)

        self.title_list.append(title)

        print(
            f"[{crawl_at}][INSERT][PRODUCT+HISTORY] tables=amazon_product,product_rank_history asin={ASIN} crawl_date={crawl_date} launch_date={launch_date} rank={rank} rank_category={rank_category}"
        )
        try:
            self.db.insert_amazon_product(
                ASIN,
                title,
                title_translation,
                subject,
                subject_translation,
                image_url,
                launch_date,
                crawl_at,
                product_type,
            )
            self.db.insert_product_rank_history(ASIN, crawl_date, rank, rank_category, crawl_at)
            self.db.commit()
            print(
                f"[{crawl_at}][OK][PRODUCT+HISTORY] inserted=amazon_product,product_rank_history asin={ASIN} crawl_date={crawl_date}"
            )
            if not self.db.record_exists(ASIN, crawl_date):
                print(
                    f"[{crawl_at}][WARN][NOT_FOUND_AFTER_COMMIT] table=product_rank_history asin={ASIN} crawl_date={crawl_date}"
                )
        except Exception as e:
            print(
                f"[{crawl_at}][FAIL][PRODUCT+HISTORY] insert_failed=amazon_product,product_rank_history asin={ASIN} crawl_date={crawl_date} err={e}"
            )
            self.db.conn.rollback()

    def _scrape_category_logic(self, url, product_type, days_limit, list_selector):
        self.driver.get(url)
        time.sleep(10)

        for page in range(3):
            page_no = self.get_current_page_number() or (page + 1)
            print(f"现在开始爬第{page_no}页")
            data_index_list = self.get_items_index_list(list_selector)
            for data_index in data_index_list:
                self.process_item(data_index, product_type)

            if not self.next_page():
                return
            time.sleep(10)

        should_stop = False

        while not should_stop:
            current_page = self.get_current_page_number()
            current_page_display = current_page if current_page is not None else "未知"
            print(f"现在开始爬第{current_page_display}页")
            data_index_list = self.get_items_index_list(list_selector)

            for cur_index, data_index in enumerate(data_index_list):
                _, launched_time_str = self.get_launch_date(data_index)

                if launched_time_str is None:
                    continue

                launched_days = self.days_to_int(launched_time_str.split("days")[0])
                print(cur_index, launched_days)

                if launched_days > days_limit:
                    should_stop = True
                    print(
                        f"第{current_page_display}页，第{cur_index + 1}个商品，距离发布时间已经超过{days_limit}天，停止爬取"
                    )
                    break
                else:
                    self.process_item(data_index, product_type)

            if should_stop:
                break

            if not self.next_page():
                break
            time.sleep(10)

        self.db.commit()

    def scrape_best_seller(self):
        self._scrape_category_logic(
            BEST_SELLER_START_URL,
            "new_peculiar",
            7,
            'xpath://div[@data-component-type="s-search-result"]',
        )


def main():
    db_manager = DatabaseManager()
    content_processor = ContentProcessor()
    scraper = AmazonScraper(db_manager, content_processor)

    try:
        scraper.scrape_best_seller()
    finally:
        db_manager.close()


if __name__ == "__main__":
    main()

