from datetime import datetime
import time
import psycopg2
from DrissionPage import ChromiumPage
from openai import OpenAI

class Config:
    # Database Configuration
    DB_HOST = "192.168.110.54"
    DB_PORT = "5432"
    DB_NAME = "overlord_db"
    DB_USER = "user1"
    DB_PASS = "user555Y1"

    # OpenAI Configuration
    OPENAI_API_KEY = "sk-d84933834d374be9a7d814d79cbcad6e"
    OPENAI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    OPENAI_MODEL = "qwen-plus"

    # URLs
    NEW_ARRIVAL_START_URL = "https://www.amazon.com/s?k=Shirt&i=fashion-novelty&s=date-desc-rank&crid=YLBANN75IKXD&qid=1767337140&sprefix=shirt%2Cfashion-novelty%2C462&xpid=BnGJNx0oBq0gz&ref=sr_pg_1"
    BEST_SELLER_START_URL = "https://www.amazon.com/s?k=Shirt&i=fashion-novelty&s=exact-aware-popularity-rank&crid=YLBANN75IKXD&qid=1767339117&sprefix=shirt%2Cfashion-novelty%2C462&xpid=BnGJNx0oBq0gz&ref=sr_st_exact-aware-popularity-rank&ds=v1%3AbGTG%2BvBKF3pkdWNuMKjeKqkR0rIwAXLQF%2BFxvBE96BY"

class DatabaseManager:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASS
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
        query = f"""
        SELECT EXISTS(
            SELECT 1
            FROM product_rank_history
            WHERE product_id = '{asin}'
            AND crawl_date = '{crawl_date}'
        )
        """
        self.cursor.execute(query)
        return self.cursor.fetchone()[0]

    def product_exists(self, asin):
        query = f"""
        SELECT EXISTS(
            SELECT 1
            FROM amazon_product
            WHERE asin = '{asin}'
        )
        """
        self.cursor.execute(query)
        return self.cursor.fetchone()[0]
        
    def check_if_crawled_today(self, asin, scrape_time):
        # Kept from original code, though unused in main logic
        self.cursor.execute("SELECT * FROM best_seller WHERE ASIN = %s AND scrape_time = %s", (asin, scrape_time))
        result = self.cursor.fetchone()
        return result is not None

    def save_product_data(self, data):
        try:
            # Extract data
            asin = data['asin']
            crawl_date = data['crawl_date']
            title = data['title']
            title_translation = data['title_translation']
            subject = data['subject']
            subject_translation = data['subject_translation']
            image_url = data['image_url']
            launch_date = data['launch_date']
            rank = data['rank']
            rank_category = data['rank_category']
            crawl_at = data['crawl_at']
            product_type = data['product_type']

            # Handle None values for SQL string construction (matching original logic)
            launch_date_sql = f"'{launch_date}'" if launch_date else 'NULL'
            rank_sql = str(rank) if rank is not None else 'NULL'
            rank_category_sql = f"'{rank_category}'" if rank_category else 'NULL'
            
            if self.record_exists(asin, crawl_date) == False:
                if self.product_exists(asin) == False:
                    # Insert into amazon_product
                    query_amazon_product = f"""
                            INSERT INTO amazon_product (asin, title, title_translation, subject, subject_translation, image_url, launch_date, created_at,product_type)
                            VALUES ('{asin}', '{title}', '{title_translation}', '{subject}', '{subject_translation}', '{image_url}', {launch_date_sql},'{crawl_at}', '{product_type}')
                    """
                    self.cursor.execute(query_amazon_product)
                
                # Insert into product_rank_history
                query_product_rank_history = f"""
                INSERT INTO product_rank_history (crawl_date, rank, rank_category, crawled_at, product_id)
                VALUES ('{crawl_date}', {rank_sql}, {rank_category_sql}, '{crawl_at}', '{asin}')
                """
                self.cursor.execute(query_product_rank_history)
                self.commit()
        except Exception as e:
            print(f"Database Error: {e}")
            self.conn.rollback()

class ContentProcessor:
    def __init__(self):
        self.client = OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL,
        )

    def _call_openai(self, messages):
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=messages
            )
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
        subject = self._call_openai(messages)
        return subject

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

## 具体翻译规范：

### A. 标题结构优化：
英文结构：主题 + 人群 + 特性 + 产品类型
中文结构：人群 + 主题 + 特性 + 产品类型

### B. 人群翻译：
- Women's → 女款/女士
- Men's → 男款/男士  
- Kids → 儿童款/童装
- Baby → 婴儿款/宝宝
- Unisex → 男女通用款

### C. 产品类型翻译：
- T-Shirt → T恤
- Long Sleeve Shirt → 长袖T恤
- V-Neck T-Shirt → V领T恤
- Hoodie → 卫衣/连帽衫
- Dress → 连衣裙
- Top → 上衣

### D. 主题/图案翻译：
- **节日主题**：准确翻译节日名称 + "主题"
- **体育主题**：球队名意译 + 赛事标准译名
- **情感主题**：使用地道中文情感词汇
- **图案描述**：准确描述图案元素和含义

### E. 特性翻译：
- 尺寸：保留数字，准确翻译单位（Years → 岁）
- 颜色：标准颜色名称
- 材质：专业术语准确
- 款式：准确描述款式特点

# 翻译示例：

## 示例1：
**原文**：Couple Cats Pickup Truck Carrying Flowers Valentine Hearts T-Shirt
**分析**：主题(情侣猫皮卡送花情人节爱心) + 产品类型(T恤)
**翻译**：情人节情侣猫咪皮卡送花爱心主题T恤

## 示例2：
**原文**：Women's Miami Hurricanes CFP Semifinal Fiesta Bowl 2026 Green V-Neck T-Shirt
**分析**：人群(女款) + 主题(迈阿密飓风队CFP半决赛嘉年华碗2026) + 特性(绿色V领) + 产品类型(T恤)
**翻译**：女款迈阿密飓风队2026年CFP半决赛嘉年华碗主题绿色V领T恤

## 示例3：
**原文**：Kids St Patricks Day Long Sleeve Shirts 3-7 Years Girls Boys Saint Patricks Day T-Shirt Lucky Shamrock Irish Heart Tops
**分析**：人群(儿童) + 主题(圣帕特里克节) + 特性(3-7岁男女童长袖) + 图案(幸运三叶草爱尔兰爱心) + 产品类型(上衣)
**翻译**：儿童圣帕特里克节主题3-7岁男女童长袖T恤 幸运三叶草爱尔兰爱心图案上衣

# 特别注意：

## 必须保留的信息：
1. ✅ 产品类型（T恤、卫衣等）
2. ✅ 目标人群（女款、男款、儿童款等）
3. ✅ 尺寸规格（3-7 Years → 3-7岁）
4. ✅ 重要年份（2026年）
5. ✅ 关键特性（V领、长袖等）

## 需要准确翻译的术语：
1. **球队/赛事**：
   - Miami Hurricanes → 迈阿密飓风队
   - CFP → 大学橄榄球季后赛
   - Fiesta Bowl → 嘉年华碗
   - Cotton Bowl → 棉花碗

2. **节日名称**：
   - Valentine's Day → 情人节
   - St Patrick's Day → 圣帕特里克节
   - Christmas → 圣诞节
   - Halloween → 万圣节

3. **设计元素**：
   - Shamrock → 三叶草
   - Heart → 爱心
   - Flowers → 花朵
   - Truck → 皮卡/卡车

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
            data_index = item_outer_block.attr('data-index')
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
        return picture.attr('src')

    def get_ASIN(self, index):
        ASIN_xpath = self.get_exact_item_xpath(index) + '//span[@class="word-title" and text()="ASIN:"]//following-sibling::span[@class="font-weight-b"]'
        ASIN = self.driver.ele(ASIN_xpath)
        return ASIN.texts()[0]

    def get_launch_date(self, index):
        try:
            launch_date_xpath = self.get_exact_item_xpath(index) + '//span[@class="mr-ext-1 mt-ext-3"]'
            launch_date_info = self.driver.ele(launch_date_xpath)
            launch_date_info = launch_date_info.texts()[1]
            launch_date = launch_date_info.split('(')[0].replace(' ', '')
            launched_time = launch_date_info.split('(')[1].split(')')[0]
            return str(launch_date), str(launched_time)
        except:
            return None, None

    def get_item_rank(self, index):
        try:
            rank_xpath = self.get_exact_item_xpath(index) + '//span[@class="font-weight-b"]/span[contains(@class,"rank-box")]'
            rank = self.driver.eles(rank_xpath)[0].texts()[0]
            rank = rank.replace('#', '').replace(',', '')
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

    def next_page(self):
        try:
            self.driver.ele('xpath://a[contains(@class,"s-pagination-next")]').click()
        except Exception as e:
            print(f"Error clicking next page: {e}")

    def days_to_int(self, days_str):
        try:
            return int(days_str.replace(',', ''))
        except:
            return 0
    
    def created_time(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def process_item(self, data_index, product_type):
        ASIN = self.get_ASIN(data_index)
        title = self.get_title(data_index)
        title_translation = self.processor.translate_title(title)
        subject = self.processor.recognize_text_from_title(title)
        subject_translation = self.processor.translate_subject(subject)
        image_url = self.get_picture(data_index)
        launch_date, launched_time = self.get_launch_date(data_index)
        rank = self.get_item_rank(data_index)
        rank_category = self.get_item_rank_category(data_index)
        
        crawl_at = self.created_time()
        crawl_date = crawl_at.split(' ')[0]
        
        self.title_list.append(title)
        
        data = {
            'title': title,
            'title_translation': title_translation,
            'image_url': image_url,
            'asin': ASIN,
            'launch_date': launch_date,
            'launched_time': launched_time,
            'rank': rank,
            'rank_category': rank_category,
            'crawl_at': crawl_at,
            'crawl_date': crawl_date,
            'subject': subject,
            'subject_translation': subject_translation,
            'product_type': product_type
        }
        
        # Print info (mimicking original logging)
        print([title, title_translation, image_url, ASIN, launch_date, launched_time, rank,
               rank_category, crawl_at, crawl_date, subject, subject_translation, product_type])
        
        print("保存到数据库")
        self.db.save_product_data(data)
        
        if product_type == "new_peculiar":
             print([title, title_translation, image_url, ASIN, launch_date, launched_time, rank, rank_category, crawl_at, subject, subject_translation,product_type])

    def _scrape_category_logic(self, url, product_type, days_limit, list_selector):
        product_type_cn = "新奇特" if product_type == "new_peculiar" else "新品榜"
        print(f"正在爬取{product_type_cn}")
        self.driver.get(url)
        time.sleep(10)

        # Scrape first 3 pages
        for page in range(3):
            print(f"现在开始爬第{page+1}页")
            item_counts = len(self.driver.eles('xpath://div[@role="listitem"]')) # Mimic get_items_count logic which is hardcoded in original
            data_index_list = self.get_items_index_list(list_selector)
            for data_index in data_index_list:
                self.process_item(data_index, product_type)
            
            self.next_page()
            time.sleep(10)

        # Continue from page 4
        current_page = 4
        should_stop = False
        
        while not should_stop:
            print(f"现在开始爬第{current_page}页")
            # item_counts logic in original is just for calling get_items_index_list(item_counts) but the arg is ignored in that function!
            # In original: def get_items_index_list(index): ... returns list based on driver.eles, ignoring index.
            data_index_list = self.get_items_index_list(list_selector)

            for cur_index, data_index in enumerate(data_index_list):
                _, launched_time_str = self.get_launch_date(data_index)
                
                if launched_time_str is None:
                    continue
                
                launched_days = self.days_to_int(launched_time_str.split('days')[0])
                print(cur_index, launched_days)

                if launched_days > days_limit:
                    should_stop = True
                    print(f"第{current_page}页，第{cur_index+1}个商品，距离发布时间已经超过{days_limit}天，停止爬取")
                    break
                else:
                    self.process_item(data_index, product_type)
            
            if should_stop:
                break

            current_page += 1
            self.next_page()
            time.sleep(10)
        
        self.db.commit()

    def scrape_new_arrival(self):
        # Original: xpath://div[@role="listitem"]
        self._scrape_category_logic(
            Config.NEW_ARRIVAL_START_URL, 
            "new_arrival", 
            1, 
            'xpath://div[@role="listitem"]'
        )

    def scrape_best_seller(self):
        # Original: xpath://div[@data-component-type="s-search-result"]
        self._scrape_category_logic(
            Config.BEST_SELLER_START_URL, 
            "new_peculiar", 
            7, 
            'xpath://div[@data-component-type="s-search-result"]'
        )

def main():
    db_manager = DatabaseManager()
    content_processor = ContentProcessor()
    scraper = AmazonScraper(db_manager, content_processor)

    try:
        scraper.scrape_best_seller()
        print("新奇特爬取完成")
        time.sleep(600)
        scraper.scrape_new_arrival()
        print("新品榜爬取完成")
    finally:
        db_manager.close()

if __name__ == '__main__':
    main()
