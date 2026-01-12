import os.path
import time

import requests
import psycopg2

class ImageDownloader:
    def __init__(self, db_host, db_port, db_name, db_user, db_password,file_path_prefix="D:/Y-Project/Overlord/Theme/"):
        self.conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        self.cursor = self.conn.cursor()
        self.valid_asin_items_list = []
        self.file_path_prefix = file_path_prefix

    def getExistAsin(self):
        self.cursor.execute("SELECT asin,image_url FROM amazon_product")
        # self.cursor.execute("SELECT * FROM amazon_order_item")
        results = self.cursor.fetchall()
        for result in results:
            asin = result[0]
            image_url = result[1]
            if image_url == '':
                print(f"Image url is empty: {asin}")
                continue
            else:
                self.valid_asin_items_list.append({asin:image_url})
        return self.valid_asin_items_list

    def generateLocalFilePath(self,asin):
        return f"{self.file_path_prefix}/static/img/theme/{asin[0:3]}/{asin}.jpg"

    def isExist(self,local_file_path):
        return os.path.exists(local_file_path)

    def downloadImageModule(self,image_url,asin):
        response = requests.get(image_url)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(self.generateLocalFilePath(asin)), exist_ok=True)
            with open(self.generateLocalFilePath(asin), 'wb') as f:
                f.write(response.content)
            print(f"Image downloaded: {self.generateLocalFilePath(asin)}")
        else:
            print(f"Failed to download image: {image_url}")

    def main(self):
        self.getExistAsin()
        for item in self.valid_asin_items_list:
            asin = list(item.keys())[0]
            image_url = item[asin]
            local_file_path = self.generateLocalFilePath(asin)
            if self.isExist(local_file_path):
                print(f"Image already exists: {local_file_path}")
                continue
            else:
                self.downloadImageModule(image_url,asin)
                time.sleep(5)


if __name__ == "__main__":
    downloader = ImageDownloader(
        db_host="192.168.110.54",
        db_port="5432",
        db_name="overlord_db",
        db_user="user1",
        db_password="user555Y1"
    )
    downloader.main()
