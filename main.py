import asyncio
import os
import time
import sys
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gtts import gTTS  # Importing gTTS for text-to-speech conversion

# Print sys.path for debugging purposes
print(sys.path)

# Ensure the audio directory exists on server startup
os.makedirs("/app/audio", exist_ok=True)

app = FastAPI()

quizzes = {}  # Temporary in-memory storage for quizzes

class Question(BaseModel):
    question_text: str
    choices: list[str]
    correct_answer: str

class Quiz(BaseModel):
    title: str
    questions: list[Question]

# Initialize ThreadPoolExecutor
executor = ThreadPoolExecutor()

# Function to generate audio using gTTS
def generate_audio(text: str, output_path: str):
    try:
        # Generate the audio using gTTS (Arabic)
        tts = gTTS(text=text, lang='ar')
        tts.save(output_path)
        print(f"Audio file saved to {output_path}")
    except Exception as e:
        print(f"Error generating audio: {e}")

# Create quiz with TTS generation
@app.post("/create-quiz/")
async def create_quiz(quiz: Quiz):
    quiz_id = str(len(quizzes) + 1)
    quizzes[quiz_id] = quiz.dict()
    os.makedirs("/app/audio", exist_ok=True)

    tasks = []
    start_time = time.time()  # Start timing the entire process

    for i, question in enumerate(quizzes[quiz_id]["questions"]):
        question_start_time = time.time()  # Start timing for each question
        audio_path = f"/app/audio/{quiz_id}_{i}.mp3"
        
        # Submit the task to the ThreadPoolExecutor
        future = executor.submit(generate_audio, question["question_text"], audio_path)
        tasks.append(future)

        question_end_time = time.time()  # End timing for each question
        print(f"Audio generation for question {i} took {question_end_time - question_start_time} seconds.")

    # Wait for all tasks to finish
    for future in tasks:
        future.result()  # This will block until the task is done

    end_time = time.time()  # End timing the entire process
    print(f"Total audio generation took {end_time - start_time} seconds.")

    # Assign generated audio URL to each question
    for i, question in enumerate(quizzes[quiz_id]["questions"]):
        audio_path = f"/app/audio/{quiz_id}_{i}.mp3"
        quizzes[quiz_id]["questions"][i]["audio_url"] = audio_path

    return {"quiz_id": quiz_id, "message": "Quiz created successfully"}

# Play audio for a quiz question
@app.get("/play-audio/{quiz_id}/{question_index}")
async def play_audio(quiz_id: str, question_index: int):
    print(f"quizzes: {quizzes}")  # Debugging statement to print the quizzes dictionary
    quiz = quizzes.get(quiz_id)
    if not quiz:
        print(f"Quiz with id {quiz_id} not found")  # Debugging statement
        raise HTTPException(status_code=404, detail="Quiz not found")
    questions = quiz.get("questions", [])
    if question_index >= len(questions):
        print(f"Question index {question_index} out of range for quiz {quiz_id}")  # Debugging statement
        raise HTTPException(status_code=404, detail="Question index out of range")
    audio_url = questions[question_index].get("audio_url")
    if not audio_url or not os.path.exists(audio_url):
        print(f"Audio file not found for question {question_index} in quiz {quiz_id}")  # Debugging statement
        raise HTTPException(status_code=404, detail="Audio not found")
    print(f"Serving audio file {audio_url} for question {question_index} in quiz {quiz_id}")  # Debugging statement
    return FileResponse(audio_url, media_type="audio/mpeg")

# Upload audio for a quiz question
@app.post("/upload-audio/{quiz_id}/{question_index}")
async def upload_audio(quiz_id: str, question_index: int, file: UploadFile = File(...)):
    # Validate quiz_id and question_index
    if quiz_id not in quizzes or question_index >= len(quizzes[quiz_id]["questions"]):
        raise HTTPException(status_code=404, detail="Quiz or question not found")
    
    # Define the file path
    audio_path = f"/app/audio/{quiz_id}_{question_index}.mp3"
    
    # Save the uploaded file
    with open(audio_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Update the quizzes dictionary with the new audio_url
    quizzes[quiz_id]["questions"][question_index]["audio_url"] = audio_path
    
    return {"message": "Audio uploaded successfully"}

# Route to serve audio files by filename
@app.get("/audio/{filename}")
async def read_audio_file(filename: str):
    file_path = f"/app/audio/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg")

# Root endpoint for health check
@app.get("/")
async def root():
    return {"message": "Arabic Quiz Form using Nipponjo TTS"}