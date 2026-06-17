台灣房價預測系統 (Taiwan House Price Prediction System)
專案簡介

本專案為個人獨立完成之資料科學與全端開發專案。

線上展示

🌐 Demo Website

https://saber591.win

專案簡報

📄 30分鐘完整專案口試簡報

房價預測系統_30分鐘口說版_v8.pdf

系統展示
房屋列表頁
<img width="1636" height="880" alt="property_list" src="https://github.com/user-attachments/assets/e290278f-16f6-43be-a9e7-f072dc69ac9d" />
房屋詳細頁
<img width="1104" height="882" alt="property_detail" src="https://github.com/user-attachments/assets/e43fc6f2-42f7-4c9b-a8b8-04e11349d0b8" />
AI 房價預測輸入頁
<img width="1168" height="810" alt="ai_predict_form" src="https://github.com/user-attachments/assets/9b521687-60a2-40c3-81a5-6c94e2347efa" />
AI 房價預測結果頁

系統整合：

實價登錄資料
591 房屋交易資料
591 預售屋資料
信義房屋資料
地理資訊資料
周邊生活機能資料

透過資料清洗、特徵工程、機器學習建模與 Web 系統開發，建立可實際使用的房價預測平台。

專案涵蓋：

資料蒐集 (Web Crawling)
ETL Pipeline
Feature Engineering
Machine Learning
Model Deployment
Django Backend
MySQL Database
Redis Cache
Linux Server Deployment
專案成果
訓練資料規模
實價登錄資料
591 預售屋資料
591 中古屋資料
信義房屋資料

總資料量超過數十萬筆房屋資訊。

模型表現
591 預售屋
指標	數值
MAE	1.10 萬元/坪
RMSE	2.05 萬元/坪
MAPE	2.87%
591 中古屋
指標	數值
MAE	3.25 萬元/坪
RMSE	5.85 萬元/坪
MAPE	11.78%
系統展示

網站首頁：

https://saber591.win

功能包含：

房屋查詢
房價預測
收藏功能
會員登入
地圖定位
周邊生活機能分析
系統架構
<img width="558" height="572" alt="system_architecture png" src="https://github.com/user-attachments/assets/5f76c9de-5e99-4bb8-8a9d-da875f3c7d32" />
房價預測流程
<img width="478" height="704" alt="prediction_pipeline png" src="https://github.com/user-attachments/assets/48395985-2549-4289-b615-911abc3cad72" />
er diagram
<img width="1964" height="1162" alt="er_diagram" src="https://github.com/user-attachments/assets/fd744359-41af-4ffe-b53f-5ec592150f6d" />

技術架構
Backend
Python
Django
Gunicorn
Nginx
Database
MySQL
Cache
Redis
Machine Learning
LightGBM
Scikit-Learn
Pandas
NumPy
Deployment
Ubuntu Linux
Cloudflare
資料來源
1. 實價登錄

提供真實成交價格資料。

主要欄位：

成交年月
房屋坪數
建物型態
屋齡
行政區
成交單價
2. 591 預售屋

自行開發爬蟲系統。

取得：

建案名稱
建商資訊
預計交屋時間
樓層規劃
房型規劃
地理位置
3. 591 中古屋

自行開發 API 爬蟲。

取得：

房屋總價
單價
坪數
格局
社區名稱
屋齡
4. 信義房屋

自行開發多執行緒爬蟲。

取得：

房屋資訊
房屋圖片
社區資訊
房屋價格
地址資訊
Feature Engineering

本專案核心價值之一為大量地理與區域特徵工程。

地理位置特徵

地址

↓

經緯度轉換

↓

唯一地理位置編碼

交通特徵

計算：

最近捷運站距離
最近火車站距離
最近高鐵站距離
POI 特徵

統計周邊：

超商
餐廳
銀行
醫院
停車場

300m / 500m 範圍數量

行情特徵

建立：

行政區歷史均價
地理位置歷史均價
月均價變化

避免資料洩漏 (Data Leakage)。

時間特徵

建立：

成交年
成交月
time_index
交易距今月數
交互特徵

建立：

坪數 × 屋齡

作為模型輸入。

機器學習模型
Model

LightGBM Regressor

目標：

預測：

單價 (萬元/坪)

訓練策略

採用：

Time-based Split
Expanding Encoding
Historical Price Feature

避免未來資料洩漏。

類別處理

使用：

Label Encoding
Hierarchical Encoding

建立：

縣市層級
行政區層級
地理位置層級
建案層級

四層結構。

資料庫設計

主要資料表：

property
property_location
property_poi_feature
property_prediction_feature
house_591_existing_detail
house_591_presale_detail
sinyi_detail

共十餘張資料表。

完整 ER Diagram 請參考：

/docs/ER_Diagram.png

系統效能優化
Redis Cache

快取：

房屋列表頁
房屋詳細頁
AI 預測結果
POI 查詢結果

降低重複查詢成本。

Database Optimization

建立：

Index
Foreign Key

提升查詢效率。

部署架構

Cloudflare

↓

Nginx

↓

Gunicorn

↓

Django

↓

MySQL + Redis

壓力測試
本機

Concurrency = 100

Property 頁面：

703 Requests/sec

Login 頁面：

3171 Requests/sec

Cloudflare

Concurrency = 100

Property 頁面：

39.56 Requests/sec

Login 頁面：

197.73 Requests/sec

系統可穩定支援百人同時瀏覽。

專案結構
final_site/

├── myapp/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── ml/
│       ├── predictor.py
│       ├── feature_builder.py
│       ├── encoding_utils.py
│       ├── geocode_utils.py
│       ├── poi_utils.py
│       └── address_utils.py

├── templates/
├── static/
├── import_pkl2.py
├── update_mysql_from_pkl.py
└── requirements.txt
執行方式
安裝套件
pip install -r requirements.txt
建立資料庫
mysql
source database_backup.sql
啟動 Redis
redis-server
啟動 Django
python manage.py runserver
大型檔案下載

由於模型與資料集超過 GitHub 容量限制，請至以下雲端連結下載：

https://drive.google.com/drive/folders/1p-9CUwkgZVmwIwgRs59oYKPs0Psq6qJD

下載後放入：

m/

資料夾即可執行系統。

作者

Johnny Hsieh

國立中央大學 電機工程學系

國立交通大學 資訊工程研究所（修業）

GitHub:
https://github.com/a2304101

專案類型：

Data Science + Machine Learning + Full Stack Development
