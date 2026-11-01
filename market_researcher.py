import os
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apify_client import ApifyClient

# تهيئة الخادم
app = FastAPI()

# السماح لواجهة Next.js بالاتصال بهذا الخادم (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    url: str

@app.post("/api/analyze")
def analyze_competitor(req: AnalyzeRequest):
    print(f"🚀 جاري تحليل الرابط: {req.url}")
    
    apify_token = os.environ.get("APIFY_API_TOKEN", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    
    if not apify_token or not gemini_key:
         print("❌ خطأ: المفاتيح غير متوفرة في بيئة Render")
         raise HTTPException(status_code=500, detail="خطأ في إعدادات الخادم: المفاتيح غير متوفرة")

    client = ApifyClient(apify_token)
    run_input = {
        "startUrls": [{"url": req.url}],
        "geminiApiKey": gemini_key,
        "maxReviews": 40
    }

    try:
        print("⏳ جاري الاتصال بـ Apify...")
        run = client.actor("5gKtPDWkYDdFCibky").call(run_input=run_input)
        
        if not run:
            print("❌ خطأ: Apify لم يرجع أي بيانات تشغيل")
            raise HTTPException(status_code=500, detail="فشل بدء التشغيل في Apify")

        run_status = run.get("status")
        dataset_id = run.get("defaultDatasetId")
        kv_store_id = run.get("defaultKeyValueStoreId")
        print(f"✅ انتهى Apify بحالة: {run_status} | Dataset: {dataset_id} | KV Store: {kv_store_id}")
        
        if run_status != "SUCCEEDED":
            raise HTTPException(status_code=500, detail=f"فشل تشغيل الأداة في Apify بحالة: {run_status}")

        # 1. المحاولة الأولى (الأضمن): جلب التقرير من Key-Value Store (OUTPUT) لتجاوز قيود الصلاحيات
        if kv_store_id:
            output_record = client.key_value_store(kv_store_id).get_record("OUTPUT")
            if output_record and output_record.get("value"):
                print("🎉 تم جلب التقرير بنجاح من Key-Value Store وإرساله إلى الواجهة!")
                return output_record["value"]

        # 2. المحاولة الثانية: جلب التقرير من Dataset التقليدية
        if dataset_id:
            dataset_items = client.dataset(dataset_id).list_items().items
            if dataset_items:
                print("🎉 تم جلب التقرير بنجاح من Dataset وإرساله إلى الواجهة!")
                return dataset_items[0] 

        print("❌ خطأ: لم يتم العثور على التقرير في KV Store أو Dataset")
        raise HTTPException(status_code=404, detail="لم يتم العثور على نتائج داخل قاعدة البيانات")
            
    except Exception as e:
        print("💥 تفاصيل الخطأ الداخلي:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))