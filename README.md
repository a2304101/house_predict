# 房價預測專案

## 資料與模型下載
由於專案內包含大型資料集與模型權重檔案，請至以下雲端連結下載後，放入 `m/` 資料夾中再執行程式：
- [歷史data.pkl (450MB)](https://drive.google.com/drive/folders/1p-9CUwkgZVmwIwgRs59oYKPs0Psq6qJD?usp=sharing)
- [歷史結果.pkl (312MB)](https://drive.google.com/drive/folders/1p-9CUwkgZVmwIwgRs59oYKPs0Psq6qJD?usp=sharing)
- [資料庫備份.sql (285MB)](https://drive.google.com/drive/folders/1p-9CUwkgZVmwIwgRs59oYKPs0Psq6qJD?usp=sharing)
- [591非預售.pkl (130MB)](https://drive.google.com/drive/folders/1p-9CUwkgZVmwIwgRs59oYKPs0Psq6qJD?usp=sharing)
- [lgb_full_train_final.txt (154MB)](https://drive.google.com/drive/folders/1p-9CUwkgZVmwIwgRs59oYKPs0Psq6qJD?usp=sharing)

- graph TD

A[591資料]
B[信義房屋]
C[實價登錄]

A --> D[資料清洗]
B --> D
C --> D

D --> E[地址轉經緯度]
E --> F[POI特徵]
F --> G[交通距離特徵]
G --> H[歷史行情特徵]
H --> I[Hierarchical Encoding]
I --> J[LightGBM]
J --> K[房價預測]
