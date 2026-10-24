import sys, re, json, subprocess, urllib.parse
def search(q, sp="CAMSBAgFEAE%3D"):
    url="https://www.youtube.com/results?search_query="+urllib.parse.quote_plus(q)+"&sp="+sp
    html=subprocess.run(["curl","-s","-L","--max-time","40","-H","Accept-Language: es-ES,es;q=0.9","-H","User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","-H","Cookie: SOCS=CAI; CONSENT=YES+","-H","Accept: text/html",url],capture_output=True,encoding="utf-8",errors="replace").stdout
    m=re.search(r"var ytInitialData = (\{.*?\});</script>",html,re.S)
    if not m: return None, len(html)
    d=json.loads(m.group(1)); out=[]
    def walk(o):
        if isinstance(o,dict):
            if "videoRenderer" in o:
                v=o["videoRenderer"]
                t="".join(r.get("text","") for r in v.get("title",{}).get("runs",[]))
                views=(v.get("viewCountText",{}) or {}).get("simpleText","")
                age=(v.get("publishedTimeText",{}) or {}).get("simpleText","")
                ch="".join(r.get("text","") for r in (v.get("ownerText",{}) or {}).get("runs",[]))
                out.append((t,views,age,ch))
            for x in o.values(): walk(x)
        elif isinstance(o,list):
            for x in o: walk(x)
    walk(d); return out, len(html)
if __name__=="__main__":
    r,n=search(sys.argv[1]); print("html bytes:",n)
    if r is None: print("sin ytInitialData (consentimiento/bloqueo)")
    else:
        for t,v,a,c in r[:8]: print(f"{v:>22} | {a:<14} | {c[:28]:<28} | {t[:70]}")
