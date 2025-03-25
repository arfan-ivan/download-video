from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
import yt_dlp as youtube_dl
import requests
import datetime
import traceback
import logging
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# Pemetaan resolusi
resolution_map = {
    'bytevc1_1080p_834143-0': '1080p',
    'bytevc1_720p_638433-0': '720p',
    'h264_540p_1235601-0': '540p',
}

# Direktori penyimpanan
save_dir = 'static/video/'
os.makedirs(save_dir, exist_ok=True)

def delete_old_files():
    now = datetime.datetime.now()
    for filename in os.listdir(save_dir):
        file_path = os.path.join(save_dir, filename)
        if os.path.isfile(file_path):
            file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            age = now - file_mtime
            if age > datetime.timedelta(hours=24):
                try:
                    os.remove(file_path)
                    logging.info(f"Deleted old file: {file_path}")
                except Exception as e:
                    logging.error(f"Error deleting file {file_path}: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(delete_old_files, 'interval', hours=1)
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

def download_image_from_url(image_url, save_path):
    response = requests.get(image_url, stream=True)
    response.raise_for_status()  # Ensure the request was successful
    with open(save_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

@app.route('/download', methods=['POST'])
def download_video():
    try:
        data = request.json
        video_url = data.get('video_url')
        resolution = data.get('resolution')
        download_audio = data.get('download_audio', False)
        download_image_flag = data.get('download_image', False)

        platform = 'unknown'
        if 'facebook.com' in video_url:
            platform = 'facebook'
        elif 'instagram.com' in video_url:
            platform = 'instagram'
        elif 'tiktok.com' in video_url:
            platform = 'tiktok'
        elif 'youtube.com' in video_url or 'youtu.be' in video_url:
            platform = 'youtube'

        if platform == 'unknown':
            raise ValueError("Platform not supported")

        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        if download_image_flag:
            filename = f'arfan_{timestamp}.jpg'
            # Download image based on the platform
            if platform in ['instagram', 'facebook']:
                # For Instagram and Facebook, extract the image URL from video URL
                image_url = extract_image_url_from_platform(video_url, platform)
            else:
                # Handle other platforms if needed
                image_url = video_url  # Fallback to video_url if no special handling required

            if image_url:
                download_image_from_url(image_url, os.path.join(save_dir, filename))
            else:
                raise ValueError("Failed to extract image URL")

        elif download_audio:
            filename = f'arfan_{timestamp}'
            ydl_opts = {
                'outtmpl': os.path.join(save_dir, filename), 
                'format': 'bestaudio/best', 
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
            }
        else:
            filename = f'arfan_{timestamp}.mp4'
            if resolution in resolution_map:
                resolution_value = resolution_map[resolution]
                format_str = f'bestvideo[height<={resolution_value}]+bestaudio/best'
            else:
                format_str = 'bestvideo+bestaudio/best'
            ydl_opts = {
                'outtmpl': os.path.join(save_dir, filename),
                'format': format_str,
                'merge_output_format': 'mp4'
            }
        
        if not download_image_flag:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # Tambahkan ekstensi .mp3 setelah proses unduhan selesai
            if download_audio:
                filename += '.mp3'

        final_file_path = os.path.join(save_dir, filename)
        if os.path.exists(final_file_path):
            return jsonify({'status': 'success', 'file_url': f'/static/video/{filename}'})
        else:
            raise FileNotFoundError(f"File not found: {final_file_path}")

    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/static/video/<filename>')
def serve_file(filename):
    return send_from_directory(save_dir, filename)

def extract_image_url_from_platform(video_url, platform):
    # Add logic to extract image URL based on the platform
    if platform == 'instagram':
        # Example logic to extract image URL from Instagram
        # This requires scraping or API usage to get the image URL from a post
        return video_url  # Placeholder, replace with actual logic
    elif platform == 'facebook':
        # Example logic to extract image URL from Facebook
        # This requires scraping or API usage to get the image URL from a post
        return video_url  # Placeholder, replace with actual logic
    # Add additional platform handling if needed
    return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
