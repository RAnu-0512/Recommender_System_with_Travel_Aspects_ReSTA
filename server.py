from flask import Flask, render_template, jsonify, request, url_for,redirect
import webbrowser
import gensim
from read_sp_info import get_spotinfo,get_popular_spotinfo
from return_aspect import return_aspect,popular_aspects,get_random_aspects
from calculate_distance import calc_near_spot
from return_spot import return_spot,get_other_pref_spot
from read_cluster_info import get_clusterinfo
from read_pref_info import get_allpref_info
from read_reviews_info import get_reviews_info
import argparse
import csv
import random
top_n = 20 #推薦スポット数
aspect_top_n = 15 #ヒットする観点数


# ------------------------------------------------------------------------------------------------------------------------------------------------
# spots_info = {spotname:{lat:lat,lng:lng,
# aspects:{apsect1:{vector:vector1,whichFrom:whichFrom,senti_score:senti_score,count:count,count_percentage:count_percentage,fastText_vector:vector},
# aspect2:{vector:vector2,...},..},
# aspectsVector:vector,numOfRev:number,major_aspects:,miner_aspects:,aspects_label:},...}
print(".....スポット情報読み込み中")
allpref_spots_info = get_spotinfo()
print(".....スポット情報読み込み完了!!")
# ------------------------------------------------------------------------------------------------------------------------------------------------
print(".....クラスタリング情報読み込み中")
allpref_clusters_info = get_clusterinfo()
print(".....クラスタリング情報読み込み完了!!")
# ------------------------------------------------------------------------------------------------------------------------------------------------
print(".....県情報読み込み中")
allpref_info = get_allpref_info(allpref_spots_info)
print(".....県情報読み込み完了!!")
# ------------------------------------------------------------------------------------------------------------------------------------------------
print(".....有名スポットの情報読み込み中")
popluar_spots_info = get_popular_spotinfo(allpref_spots_info) #allpref_spots_infoと同じ形式  # テスト用の時コメントアウト
print(".....有名スポットの情報読み込み完了")
list_spots_popular = get_other_pref_spot(popluar_spots_info) # テスト用の時コメントアウト
# list_spots_popular = get_other_pref_spot(allpref_spots_info) #本番環境ではコメントアウト
list_spots_all = get_other_pref_spot(allpref_spots_info)
# ------------------------------------------------------------------------------------------------------------------------------------------------
print(".....レビュー情報読み込み中")
allpref_reviews_info = get_reviews_info() #all_pref_reviews_info-->{pref:{spotname:{aspect:[{"entity":entity,"review":review}]}} 
print(".....レビュー情報読み込み完了")
# ------------------------------------------------------------------------------------------------------------------------------------------------
print(".....word2vecモデル読み込み中")
#相対パス(relative_path)
model_path = "../word2vec/cc.ja.300.vec.gz"
model = "test_model"  #テストするときのモデル 

#<注意>word2vecモデルがない方は下の行をコメントアウトしてください　word2vecモデルを準備している方はコメントを外してください。
model = gensim.models.KeyedVectors.load_word2vec_format(model_path, binary=False) #モデルの読み込み 
print(".....word2vecモデル読み込み完了!!")
# ------------------------------------------------------------------------------------------------------------------------------------------------

returned_aspect_list = []
returned_distance_range = 0

app = Flask(__name__)

@app.route("/", methods= ["POST",'GET'])
def start_page():
    print("server sucsess")
    return render_template("start_travel_recommend.html")

@app.route("/<pref>", methods=["POST","GET"])
def return_pref_html(pref):
    print(f"{pref} html")
    return render_template("travel_recommend.html",pref=pref) 

@app.route("/get_prefLatLng", methods=["POST"])
def get_prefLatLng():
    data = request.get_json()
    pref = data.get('pref')
    print(f"select : {pref}")
    startLatLng_path = "./data/start_latlng/start_latlng.csv"
    with open(startLatLng_path,"r",encoding="UTF-8") as f_r:
        reader = csv.reader(f_r)
        for row in reader:
            print(row)
            pref_r = row[0]
            lat = float(row[1])
            lng = float(row[2])
            if pref_r == pref:
                return {"pref":pref,"start_lat": lat , "start_lng":lng}
    return {"pref":"Error","start_lat": 0 , "start_lng":0}

@app.route("/get_recommended_spots",methods=["POST"])
def get_recommended_spots():
    data = request.get_json()
    lat = float(data.get('clicked_lat'))
    lng = float(data.get('clicked_lng'))
    pref = data.get("selected_pref").replace("県","").replace("京都府","京都").replace("東京都","東京").replace("大阪府","大阪")
    rec_range = int(data.get('range'))
    selected_aspects = data.get('selected_aspects') #[{"aspect":asp1,"priority":prio1},{...}]
    selected_styles = data.get("selected_style").split("\n")
    selected_spots = data.get("selectedSpots")
    popularityLevel = int(data.get("popularityLevel"))

    print(f"lat : {lat}\nlng : {lng}\npref : {pref}\nrec_range : {rec_range}\n selected_aspects : {selected_aspects}\n selected_styles: {selected_styles}\n selected_spots: {selected_spots}\n 推薦するスポットタイプ: {popularityLevel}")
    spots_info = allpref_spots_info[pref]
    cluster_info = allpref_clusters_info[pref]
    pref_info = allpref_info[pref]

    #返却形式は[[spot_name,{"lat":lat,"lng":lng,"aspects":{aspect1:{senti_score:senti_score,count:count},..},"similar_aspects":{},major_aspects:{},miner_aspects:{},"score":score,"spot_url":url,
    # "selectAspectSim":sim1,"selectStyleSim":sim2,"selectSpotSim":sim3,"popularWight":popular_wight}],[spot_name,{}], ...]
    recommend_spots = return_spot(lat,lng,rec_range,selected_aspects,allpref_spots_info,cluster_info,pref_info,selected_styles,selected_spots,popularityLevel,pref,top_n) 
    
    if recommend_spots:
        print("recommend_spots: ", [sublist[0] for sublist in recommend_spots[:5]],"等")
    response_data = []
    #    response_data = {'spot_name': sp_info[0] , 'lat': sp_info[1][0], 'lng': sp_info[1][1], "distance": sp_info[-1] }
    for recommend_spot in recommend_spots:
        converted_data = {
            "spot_name" : recommend_spot[0],
            "lat" : recommend_spot[1]["lat"],
            "lng" : recommend_spot[1]["lng"],
            "aspects" : recommend_spot[1]["aspects"],
            "aspects_label" : recommend_spot[1]["aspects_label"],
            "similar_aspects" : recommend_spot[1]["similar_aspects"],
            "similar_aspects_label" : recommend_spot[1]["similar_aspects_label"],
            "major_aspects" :recommend_spot[1]["major_aspects"],
            "major_aspects_label" : recommend_spot[1]["major_aspects_label"],
            "miner_aspects" :recommend_spot[1]["miner_aspects"],
            "miner_aspects_label" : recommend_spot[1]["miner_aspects_label"],
            "score" : recommend_spot[1]["score"],
            "selectAspectSim" : recommend_spot[1]["selectAspectSim"],
            "selectStyleSim" : recommend_spot[1]["selectStyleSim"],
            "selectSpotSim" : recommend_spot[1]["selectSpotSim"],
            "popularWight" : recommend_spot[1]["popularWight"],
            "url" : recommend_spot[1]["spot_url"],
            "homepage_name" : recommend_spot[1]["homepage_name"],
            "img_url" : recommend_spot[1]["img_url"]
        }
        response_data.append(converted_data)
        # print("converted_data : ",converted_data)
    return jsonify(response_data)
@app.route("/get_random_reviews",methods = ["POST"])
def get_random_reviews():
    data=request.get_json()
    pref = data.get("prefecture")
    spot_name = data.get("spot_name")
    aspect = data.get("aspect")
    try:
        reviewsEntityPair = allpref_reviews_info[pref][spot_name][aspect]
    except KeyError:
        reviewsEntityPair = allpref_reviews_info[pref][spot_name+"second"][aspect]
    return jsonify(random.sample(reviewsEntityPair, min(len(reviewsEntityPair), 20)) )

@app.route("/get_random_spot",methods=["POST"])
def get_random_spot():
    global list_spots_popular
    data=request.get_json()
    pref = data.get("selected_pref").replace("県","").replace("京都府","京都").replace("東京都","東京").replace("大阪府","大阪")
    print(f"get_random_spot selected_pref:{pref}")
    random_spots = random.sample(list_spots_popular, min(len(list_spots_popular), 15)) 
    return {"random_spots":random_spots}

@app.route("/search_spot", methods=["POST"])
def search_spot():
    global list_spots_all
    data = request.get_json()
    query = data.get("query")
    
    #{"spot_name":spotname,"prefectrue":cur_pref,"aspects":new_aspects,"spot_url":url}
    # # 完全一致するスポットを抽出
    exact_matches = [spotinfo for spotinfo in list_spots_all if spotinfo["spot_name"] == query]
    # 部分一致するスポットを抽出（完全一致は除く）
    partial_matches = [spotinfo 
                       for spotinfo in list_spots_all 
                       if (query in spotinfo["spot_name"] or query.replace("県","").replace("京都府","京都").replace("東京都","東京").replace("大阪府","大阪") == spotinfo["prefecture"]) 
                       and spotinfo["spot_name"] != query]
    # 結果を結合：完全一致が先頭に、部分一致が続く
    # print(f"検索スポット結果:{exact_matches + partial_matches}")
    return {"search_spots" : exact_matches + partial_matches}
    
    
@app.route("/search_form", methods=["POST"])
def get_search_keyword():
    print("get serach keyword")
    data=request.get_json()
    search_keyword = data.get("search_keyword")
    pref = data.get("selected_pref").replace("県","").replace("京都府","京都").replace("東京都","東京").replace("大阪府","大阪")
    print("selected_pref : ", pref)
    print("serach_keyword : " ,search_keyword)
    spots_info = allpref_spots_info[pref]
    results = return_aspect(search_keyword,spots_info,aspect_top_n,model)
    checkboxes = [{"label": result, "value": result} for result in results]
    return jsonify({"keyword": checkboxes})

@app.route("/recommend_aspects",methods = ["POST"])
def recommend_aspects():
    print("recommend aspects")
    data=request.get_json()
    pref = data.get("selected_pref").replace("県","").replace("京都府","京都").replace("東京都","東京").replace("大阪府","大阪")
    print("おすすめ観点クリック> selected_pref : ", pref)
    pref_info = allpref_info[pref]
    recommended_aspects = popular_aspects(pref_info,aspect_top_n)
    return_aspects = [{"label": result, "value": result} for result in recommended_aspects]
    return jsonify({"recommend_aspects": return_aspects})

@app.route("/random_aspects", methods = ["POST"])
def random_aspects():
    print("random aspects")
    data=request.get_json()
    pref = data.get("selected_pref").replace("県","").replace("京都府","京都").replace("東京都","東京").replace("大阪府","大阪")
    print("ランダム観点クリック> random_aspects : ", pref)
    spots_info = allpref_spots_info[pref]
    random_aspects = get_random_aspects(spots_info,aspect_top_n)
    return_aspects = [{"label": result, "value": result} for result in random_aspects]
    return jsonify({"random_aspects": return_aspects})

def parse_args():
    parser = argparse.ArgumentParser(description='Process some arguments.')
    parser.add_argument('--port', dest='port_num', type=int, help='Port number to be assigned')
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    port_num = args.port_num

    if port_num is not None:
        print(f'Port number is set to {port_num}')
    else:
        port_num = 8000
        print('Port number is not provided.')

    #webbrowser.open('http://localhost:'+ port_num)
    app.run(debug=True,host='0.0.0.0', port=port_num, threaded=True, use_reloader=False)

if __name__ == "__main__":
    main()
    
