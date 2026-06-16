import pickle

with open(r"F:/桃竹苗/final/m/encoding_assets.pkl", "rb") as f:
    assets = pickle.load(f)

print(assets.keys())

print("dist_map sample:")
for i, item in enumerate(assets["dist_map"].items()):
    print(item)
    if i >= 10:
        break

print("city_map sample:")
for i, item in enumerate(assets["city_map"].items()):
    print(item)
    if i >= 10:
        break

print("global_final_mean:", assets["global_final_mean"])