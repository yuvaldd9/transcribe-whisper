# 🎤 Audio Transcription Service

A simple, user-friendly web application that converts audio files to text using OpenAI's Whisper API. Perfect for transcribing meetings, interviews, podcasts, and more!

## 🌟 Features

- **Easy to Use**: Simple drag-and-drop web interface
- **Large File Support**: Automatically splits files larger than 20MB
- **Multiple Formats**: Supports MP3, WAV, FLAC, M4A, OGG, WMA, AAC, MP4, AVI, MOV, MKV
- **Speaker Identification**: Uses OpenAI's Whisper for accurate transcription
- **Download & Copy**: Easy options to save or copy your transcripts
- **Docker Ready**: Runs in a container for easy deployment

## 🚀 Quick Start

### Prerequisites

1. **Docker Desktop** - Download and install from [docker.com](https://www.docker.com/products/docker-desktop/)
2. **OpenAI API Key** - Get yours from [OpenAI Platform](https://platform.openai.com/account/api-keys)

### Installation Steps

1. **Download all files** to a folder on your computer
2. **Set up your API key**:
   - Open the `.env` file in a text editor
   - Replace `your_openai_api_key_here` with your actual OpenAI API key
   - Save the file

3. **Run the installer**:
   - Double-click `install.bat`
   - Wait for the installation to complete
   - The web interface will open automatically

4. **Start transcribing**:
   - Access the service at `http://localhost:5000`
   - Drag and drop your audio file
   - Wait for the transcription to complete
   - Copy or download your transcript!

## 📁 Project Structure

```
transcription-service/
├── Dockerfile              # Container configuration
├── docker-compose.yml      # Service orchestration
├── requirements.txt        # Python dependencies
├── app.py                  # Main application
├── templates/
│   └── index.html          # Web interface
├── .env                    # API key configuration
├── install.bat             # Installation script
├── stop.bat               # Stop service script
├── restart.bat            # Restart service script
├── logs.bat               # View logs script
├── uploads/               # Temporary file storage
├── temp_files/            # Temporary processing files
└── README.md              # This file
```

## 🛠️ Management Scripts

- **install.bat** - First-time setup and installation
- **stop.bat** - Stop the transcription service
- **restart.bat** - Restart the service
- **logs.bat** - View service logs for troubleshooting

## 🔧 Technical Details

### How It Works

1. **File Upload**: User uploads audio/video file via web interface
2. **Size Check**: System checks if file is larger than 20MB
3. **File Splitting**: Large files are split into 5-6MB chunks using FFmpeg
4. **Transcription**: Each chunk is sent to OpenAI's Whisper API
5. **Reassembly**: All transcripts are combined into a single text
6. **Delivery**: User can copy to clipboard or download as text file

### Supported Formats

- **Audio**: MP3, WAV, FLAC, M4A, OGG, WMA, AAC
- **Video**: MP4, AVI, MOV, MKV (audio is extracted)
- **Max File Size**: 500MB per file

### API Usage

- Uses OpenAI's Whisper-1 model
- Automatic speaker identification
- Handles multiple languages
- Optimized for conversation transcription

## 🐛 Troubleshooting

### Common Issues

1. **"Docker not found"**
   - Install Docker Desktop and make sure it's running
   - Restart your computer after installation

2. **"API key error"**
   - Check your `.env` file has the correct API key
   - Verify your OpenAI account has credits
   - Make sure there are no extra spaces in the API key

3. **"Service won't start"**
   - Run `logs.bat` to see error messages
   - Make sure port 5000 is not used by another program
   - Try running `restart.bat`

4. **"Transcription failed"**
   - Check your internet connection
   - Verify your OpenAI API key is valid
   - Make sure your audio file is not corrupted

### Getting Help

1. Run `logs.bat` to view detailed error messages
2. Check the Docker Desktop dashboard for container status
3. Verify all files are in the correct locations
4. Ensure your `.env` file is properly configured

## 💡 Usage Tips

### For Best Results

- Use clear, high-quality audio recordings
- Minimize background noise
- Speak clearly and at a moderate pace
- For long files, consider splitting them manually for faster processing

### File Management

- The service automatically cleans up temporary files
- Original files are deleted after processing for privacy
- Transcripts are only stored temporarily in your browser

## 🔒 Privacy & Security

- All processing happens locally in your Docker container
- Files are not stored permanently on the system
- Only transcription data is sent to OpenAI's API
- No data is shared with third parties

## 💰 Cost Considerations

- OpenAI charges for Whisper API usage
- Approximately $0.006 per minute of audio
- A 1-hour audio file costs about $0.36
- Monitor your usage in the OpenAI dashboard

## 🆕 Updates

To update the service:
1. Download the new files
2. Run `stop.bat`
3. Replace the old files with new ones
4. Run `install.bat`

## 📞 Support

For technical issues:
- Check the troubleshooting section above
- Review the logs using `logs.bat`
- Ensure all prerequisites are properly installed

---

**Made with ❤️ for easy audio transcription**