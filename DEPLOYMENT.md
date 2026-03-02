# 100% Free Deployment Guide: Resume-Job Matching Engine

Your application architecture uses a **decoupled deployment model** to optimize costs and capabilities. We've selected platforms that provide completely $0.00/mo hosting while providing the raw system resources needed to run heavy machine learning workloads.

*   **Frontend (React/Vite)**: Deployed to Vercel (Fast, global CDN, serverless).
*   **Backend (FastAPI)**: Deployed to Hugging Face Spaces (Offers a free 16 GB RAM Docker environment capable of running PyTesseract, Poppler, and heavy spaCy models).

Follow the steps below to take your application live for free.

---

## 🏗️ Phase 1: Deploy the Backend (Hugging Face Spaces)

Hugging Face Spaces is uniquely suited for machine learning backends because its free "Docker Blank" tier gives you **16 GB of RAM and 2 vCPUs**. Your codebase is already configured for this via the custom `Dockerfile`.

1. Go to [Hugging Face](https://huggingface.co/) and create a free account.
2. In the top right, click your profile icon and select **New Space**.
3. Configure the new space:
   * **Space name**: e.g., `ats-optimization-engine`
   * **License**: Choose your preference (e.g., MIT or apache-2.0)
   * **Select the Space SDK**: Choose **Docker** -> **Blank**.
   * **Space Hardware**: Keep it on the **Free (2 vCPU, 16 GB RAM)** tier.
   * Click **Create Space**.
4. You will be greeted with instructions to clone the repository to your local machine.
5. Alternatively, just click **Files and versions** at the top. Click **Add file** -> **Upload files**.
6. Upload the ENTIRE contents of your project root (especially the `Dockerfile`, `requirements.txt`, and all `.py` files).
   * *Note: Hugging face lets you drag-and-drop your codebase right into the browser.*
   * Do **NOT** upload data folders, `node_modules`, or the `.git` directory. The `.dockerignore` file serves as a good reference for what to exclude.
7. Once your files are uploaded to the Space, it will automatically say **Building** at the top of the screen.
8. Wait for the build (downloding `en_core_web_md` and `tesseract` will take about 5-8 minutes).
9. Once the status shows **Running**, click the three little dots (`...`) in the top right of your Space, select **Embed this Space**, and locate the **Direct URL** (it will look something like `https://username-ats-optimization-engine.hf.space`).
10. Copy this URL. This is your **Backend API Base URL**.

---

## 🌐 Phase 2: Deploy the Frontend (Vercel)

Now deploy the beautiful UI and link it to the Hugging Face engine.

1. Push your entire codebase to a GitHub repository if you haven't already.
2. Sign in to [Vercel](https://vercel.com/) and click **Add New** -> **Project**.
3. Import your GitHub repository.
4. In the project configuration screen:
   * **Framework Preset**: Vite
   * **Root Directory**: Select `frontend` (Click Edit, choose the `frontend` folder).
5. **Environment Variables**:
   * **Name**: `VITE_API_BASE_URL`
   * **Value**: *Paste the Direct URL you got from Hugging Face* (e.g., `https://username-ats-optimization-engine.hf.space`)
   * Make sure there is **no trailing slash ('/')** at the end of the URL.
6. Click **Deploy**.

---

## 🧪 Phase 3: Setup & Verification

Once both are deployed:

1. Visit your Vercel frontend URL.
2. Go to the **Train Engine** page. (The first time you wake up the backend, it may take 10 seconds to spin up).
3. Test the **Upload Job Data** functionality by uploading a CSV/JSON file to seed the remote database.
4. Click **Train All Roles** to generate your models on the live server.
5. Go to the **Analyze** tab and upload a sample resume.
6. Verify that it correctly processes and returns the detailed analysis using the live Hugging Face container!

## Note on Local Development
For local testing, the frontend will automatically proxy `/api` requests to `http://localhost:8000` via Vites proxy rules (so you don't need `VITE_API_BASE_URL` locally). Just run `npm run dev` in frontend and `uvicorn server:app --reload` at the root!
