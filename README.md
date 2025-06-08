# AI Companion (Multi-Turn)

A Flask-based AI companion that maintains multi-turn conversation context, powered by Gemini 2.0 Flash and PostgreSQL (Cloud SQL). Each exchange (User → AI) is stored in a database, and every AI response is generated based on the full conversation history.

The AI Companion is now available at https://ai-companion-127814990731.us-central1.run.app/. Click on the link to access and talk to your new friend. 

Below is a quick walkthrough if you want to replicate the AI Companion from scratch.

## Project Structure

```
my_ai_conpanion/
├── main.py
├── data_processing.py
├── requirements.txt
├── Dockerfile
├── .gitignore
├── .env
├── README.md
└── index.html
```

- **main.py**: Flask application handling user input, building conversation history, calling Gemini via `data_processing.py`, and logging to the database.
- **data_processing.py**: Formats the full conversation history (plus few-shot examples) and calls the Gemini model.
- **requirements.txt**: All Python dependencies.
- **Dockerfile**: Builds a Docker image with all dependencies and runs the Flask app via Gunicorn.
- **.env**: Example environment file. Copy to `.env` and fill in your credentials.
- **README.md**: This file.
- **index.html**: Front-end template showing the full multi-turn chat.

## Prerequisites

1. **Google Cloud Project** with Cloud SQL Admin API enabled.
2. **Cloud SQL (PostgreSQL) instance** created. Note the instance connection name (e.g., `my-project:us-central1:my-instance`).
3. **Gemini 2.0 Flash API access** via Google Gen AI SDK.
4. **Docker** (to build and run the container locally).
5. **gcloud CLI** (to push images to Container Registry and deploy to Cloud Run).

## Setup

1. **Create an .env file and set the following variables**:

   ```
   CLOUDSQL_USER=your_db_user
   CLOUDSQL_PASS=your_db_password
   CLOUDSQL_DB=your_database_name
   CLOUDSQL_CONNECTION_NAME=your-project:us-central1:your-instance

   GEMINI_MODEL_ID=gemini-2.0-flash-lite

   GOOGLE_CLOUD_PROJECT=your-gcp-project-id
   GOOGLE_CLOUD_LOCATION=us-central1
   GOOGLE_GENAI_USE_VERTEXAI=true
   ```

2. **(Optional) Create a Python virtual environment**:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

1. **Authenticate and set your project**:

   ```bash
   gcloud auth login

   ```

2. **Build the Docker image**:

   ```bash
   docker build -t gcr.io/$GOOGLE_CLOUD_PROJECT/ai-companion:latest .
   ```

3. **Push the image to Container Registry**:

   ```bash
   docker push gcr.io/$GOOGLE_CLOUD_PROJECT/ai-companion:latest
   ```

4. **Grant Cloud Run service account Cloud SQL Client role**:

   ```bash
   gcloud run services add-iam-policy-binding ai-companion      --member="serviceAccount:$(gcloud run services describe ai-companion --platform managed --region us-central1 --format 'value(spec.template.spec.serviceAccount)')"      --role="roles/cloudsql.client"
   ```

5. **Deploy to Cloud Run**:

   ```bash
   gcloud run deploy ai-companion      --image gcr.io/$GOOGLE_CLOUD_PROJECT/ai-companion:latest      --platform managed      --region us-central1      --allow-unauthenticated      --update-env-vars CLOUDSQL_USER=$CLOUDSQL_USER,CLOUDSQL_PASS=$CLOUDSQL_PASS,CLOUDSQL_DB=$CLOUDSQL_DB,CLOUDSQL_CONNECTION_NAME=$CLOUDSQL_CONNECTION_NAME,GEMINI_MODEL_ID=$GEMINI_MODEL_ID,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI
   ```

   After deployment, note the service URL.

## Usage

1. **Visit the URL** of your Cloud Run service. Note: you can access https://ai-companion-127814990731.us-central1.run.app/ to talk to your AI companion right away without re-deployment.
2. **Type a message** into the text box and hit **Send**.
3. **The AI Companion** will reply, and the entire multi-turn conversation will appear.
4. Hit **Restart Conversation** to start a new conversation. Note: if you see past conversations appear after coming back, hit **Restart Conversation**to clear the history and start a new one.

---
