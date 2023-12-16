from gbfs.services import SystemDiscoveryService
import pandas as pd

ds = SystemDiscoveryService()

# システム一覧を取得
system_list = ds.systems

# ステーション一覧格納用の空DataFrameを用意
column = ["country_code", "system_name", "system_id", "station_id", "station_name", "lon", "lat"]
df = pd.DataFrame(columns=column)

# ログ情報格納用の空DataFrameを用意
log_columns = ["system_id", "status", "message", "System_Name", "Auto-Discovery URL"]
df_log = pd.DataFrame(columns=log_columns)

# システム一覧の中のシステム（サービス）を順番に処理
for system in system_list:
    # システム一覧より情報を取得
    country_code = system["Country Code"]
    system_name = system["Name"]
    system_id = system["System ID"]
    url = system["Auto-Discovery URL"]
    
    # systemID使って該当サービスのクライアントを生成
    try:
        # まずは英語のGBFSデータの取得をトライ
        client = ds.instantiate_client(system_id, "en")
    except BaseException as e:
        # 英語でのデータ公開がない場合、エラーメッセージをもとに第一言語を特定
        error_message = str(e)
        first_language = error_message.split(":")[1].split(",")[0].replace(" ", "")

        try:
            # 第一言語で再取得をトライ
            client = ds.instantiate_client(system_id, first_language)
        except:
            # それでも失敗した場合は本サービスのデータ取得は諦める
            print("言語情報の取得失敗," + system_id)
            new_log = pd.DataFrame([{"system_id": system_id, "status": "Failed", "message": "Language detection failed", "System_Name": system_name, "Auto-Discovery URL": url}])
            df_log = pd.concat([df_log, new_log], ignore_index=True)
            continue

    # 生成したクライアントの中にステーション情報が存在するか確認
    if "station_information" in client.feed_names:
        # ステーション情報が存在したとき、ステーション情報の取得を試みる
        try:
            # 取得に成功したときステーション情報を配列に格納
            stations = [
                [
                    country_code,
                    system_name,
                    system_id,
                    station["station_id"],
                    station["name"],
                    station["lon"],
                    station["lat"],
                ]
                for station in client.request_feed("station_information").get("data").get("stations")
            ]
            # ステーション情報の配列をDataFrameに追加
            df = pd.concat([df, pd.DataFrame(stations, columns=column)], ignore_index=True)
            print("ステーション取得成功！," + system_id)
            new_log = pd.DataFrame([{"system_id": system_id, "status": "Success", "message": "Stations retrieved", "System_Name": system_name, "Auto-Discovery URL": url}])
            df_log = pd.concat([df_log, new_log], ignore_index=True)
        except:
            # 取得に失敗したとき、本サービスのデータ取得は諦める
            print("ステーション情報取得失敗," + system_id)
            new_log = pd.DataFrame([{"system_id": system_id, "status": "Failed", "message": "Station information retrieval failed", "System_Name": system_name, "Auto-Discovery URL": url}])
            df_log = pd.concat([df_log, new_log], ignore_index=True)
            continue
    else:
        # ステーション情報が存在しないとき、ステーション情報が無いサービス（恐らくドッグレス型サービス）なのでデータ取得処理は行わない
        print("ステーション情報なし, " + system_id)
        new_log = pd.DataFrame([{"system_id": system_id, "status": "No Data", "message": "No station information available", "System_Name": system_name, "Auto-Discovery URL": url}])
        df_log = pd.concat([df_log, new_log], ignore_index=True)

# DataFrameをCSVファイルとして出力
df.to_csv("stations.csv", index=False)
df_log.to_csv("stations_log.csv", index=False)
