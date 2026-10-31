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

# تحديد شكل البيانات القادمة من Next.js
class AnalyzeRequest(BaseModel):
    url: str

@app.post("/api/analyze")
def analyze_competitor(req: AnalyzeRequest):
    print(f"🚀 جاري تحليل الرابط: {req.url}")
    
    # جلب المفاتيح من متغيرات البيئة بشكل آمن
    apify_token = os.environ.get("APIFY_API_TOKEN")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not apify_token or not gemini_key:
         print("❌ خطأ: المفاتيح غير متوفرة في بيئة Render")
         raise HTTPException(status_code=500, detail="خطأ في إعدادات الخادم: المفاتيح غير متوفرة")

    client = ApifyClient(apify_token)
    run_input = {
        "startUrls": [{"url": req.url}],
        "geminiApiKey": gemini_key,
        "maxReviews": 100
    }

    try:
        # قمنا بإزالة الكلمة الخاطئة لأن الأداة تنتظر النتيجة تلقائياً
        print("⏳ جاري الاتصال بـ Apify (قد يستغرق الأمر دقيقة أو أكثر)...")
        run = client.actor("linenlike_summer/ai-review-miner").call(run_input=run_input)
        print("✅ اكتمل الاتصال واستخراج البيانات من Apify")
        
        # استخراج المعرف
        if isinstance(run, dict):
            dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
        else:
            dataset_id = getattr(run, "default_dataset_id", getattr(run, "defaultDatasetId", None))

        if not dataset_id:
            print("❌ خطأ: لم يتم العثور على قاعدة البيانات")
            raise HTTPException(status_code=500, detail="لم يتم العثور على قاعدة البيانات")

        # جلب التقرير وإرساله إلى Next.js
        dataset_items = client.dataset(dataset_id).list_items().items
        if dataset_items:
            print("🎉 تم إرسال التقرير بنجاح إلى الواجهة")
            return dataset_items[0] 
        else:
            print("❌ خطأ: قاعدة البيانات فارغة")
            raise HTTPException(status_code=404, detail="لم يتم العثور على نتائج")
            
    except Exception as e:
        print("💥 حدث خطأ داخلي في الخادم:")
        traceback.print_exc() # هذا السطر سيطبع سبب المشكلة بدقة متناهية في Render
        raise HTTPException(status_code=500, detail=str(e))