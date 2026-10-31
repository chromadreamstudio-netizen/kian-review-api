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
        "maxReviews": 50
    }

    try:
        print("⏳ جاري الاتصال بـ Apify...")
        # استخدام المعرف المباشر للأداة لضمان الوصول الفوري
        run = client.actor("5gKtPDWkYDdFCibky").call(run_input=run_input)
        
        if not run:
            print("❌ خطأ: Apify لم يرجع أي بيانات تشغيل (تحقق من صلاحية API Token)")
            raise HTTPException(status_code=500, detail="فشل بدء التشغيل في Apify")

        run_status = run.get("status")
        dataset_id = run.get("defaultDatasetId")
        print(f"✅ انتهى Apify بحالة: {run_status} | معرف قاعدة البيانات: {dataset_id}")
        
        if run_status != "SUCCEEDED":
            raise HTTPException(status_code=500, detail=f"فشل تشغيل الأداة في Apify بحالة: {run_status}")

        # جلب التقرير وإرساله إلى Next.js
        dataset_items = client.dataset(dataset_id).list_items().items
        if dataset_items:
            print("🎉 تم جلب التقرير بنجاح وإرساله إلى الواجهة!")
            return dataset_items[0] 
        else:
            print("❌ خطأ: الأداة عملت في Apify ولكنها لم تحفظ نتائج (تحقق من مفتاح Gemini أو الرابط)")
            raise HTTPException(status_code=404, detail="لم يتم العثور على نتائج داخل قاعدة البيانات")
            
    except Exception as e:
        print("💥 تفاصيل الخطأ الداخلي:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))