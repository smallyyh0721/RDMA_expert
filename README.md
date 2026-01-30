# NVIDIA/Mellanox Documentation Downloader

A Python program to automatically download RDMA network card, DPU, switch, and troubleshooting documentation from NVIDIA/Mellanox.

## Features

- **Comprehensive Documentation Coverage**: Downloads manuals for:
  - ConnectX series network adapters (ConnectX-3 through ConnectX-8)
  - BlueField DPU series (BlueField-2 and BlueField-3)
  - Spectrum Ethernet switches
  - MLNX_OFED driver documentation
  - Troubleshooting guides

- **Smart Download Management**:
  - Rate limiting with configurable delays (1-3 seconds between requests)
  - Automatic retry with exponential backoff
  - User-Agent rotation to avoid IP blocking
  - Progress bars for large file downloads
  - Resume support (skips already downloaded files)

- **Organized File Structure**:
  ```
  downloads/
  ├── ConnectX/
  │   ├── ConnectX-3/
  │   ├── ConnectX-4/
  │   ├── ConnectX-5/
  │   ├── ConnectX-6/
  │   ├── ConnectX-6 Dx/
  │   ├── ConnectX-7/
  │   └── ConnectX-8/
  ├── BlueField/
  │   ├── BlueField-2/
  │   └── BlueField-3/
  ├── Spectrum_Switches/
  │   ├── Spectrum-2/
  │   ├── Spectrum-3/
  │   └── Spectrum-SN2000/
  ├── MLNX_OFED/
  │   ├── v23.04/
  │   ├── v24.01/
  │   └── v5.7/
  └── Troubleshooting/
      ├── ConnectX-5/
      ├── ConnectX-6 Dx/
      └── OFED/
  ```

- **Robust Error Handling**:
  - HTTP 429 (Too Many Requests) handling
  - Timeout management
  - Comprehensive logging to file and console
  - Failed download tracking and reporting

## Requirements

- Python 3.7 or higher
- Internet connection

## Installation

1. Clone or download this repository
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the program with:

```bash
python download_nvidia_docs.py
```

The program will:
1. Create the necessary directory structure
2. Download all documentation files
3. Display progress for each download
4. Generate a comprehensive log file (`download_nvidia_docs.log`)
5. Print a summary of successful and failed downloads

## Configuration

You can customize the program by modifying the `Config` class in `download_nvidia_docs.py`:

### Download Settings

```python
DOWNLOAD_DIR = Path("downloads")  # Base download directory
MAX_RETRIES = 3                   # Maximum retry attempts
BASE_DELAY = 1                    # Base delay in seconds
REQUEST_DELAY_MIN = 1.0           # Minimum delay between requests
REQUEST_DELAY_MAX = 3.0           # Maximum delay between requests
TIMEOUT_CONNECT = 10              # Connection timeout in seconds
TIMEOUT_READ = 30                 # Read timeout in seconds
```

### Adding New Documents

To add new documentation URLs, modify the `DOCUMENTS` dictionary in the `Config` class:

```python
DOCUMENTS = {
    "Category_Name": [
        {
            "name": "Document Name",
            "url": "https://docs.nvidia.com/...",
            "subcategory": "Subdirectory Name",
            "type": "pdf"  # or "html"
        },
    ],
}
```

## Safety Features

### Rate Limiting
- Minimum 1 second delay between requests
- Random delay up to 3 seconds between requests
- Additional sleep time when encountering rate limits

### Retry Logic
- Automatic retry on timeout (3 attempts)
- Exponential backoff for retries
- Special handling for HTTP 429 (5s sleep per retry)
- Server error retry (500-599)

### Request Headers
- Random User-Agent rotation
- Proper Accept headers
- Connection keep-alive

## Output

### Console Output
- Real-time progress information
- Download progress bars
- Status updates for each document
- Final summary of downloads

### Log File
All operations are logged to `download_nvidia_docs.log` including:
- Timestamps for all operations
- Detailed error messages
- Download status
- Failed download information

## Troubleshooting

### Connection Issues
If you encounter connection issues:
1. Check your internet connection
2. Verify the URLs are accessible
3. Review the log file for specific errors
4. Increase timeout values if needed

### Rate Limiting
If you receive many 429 errors:
1. Increase `REQUEST_DELAY_MIN` and `REQUEST_DELAY_MAX`
2. Run the program during off-peak hours
3. Some downloads may take longer due to rate limiting

### Partial Downloads
If the program is interrupted:
1. Simply run it again - it will skip already downloaded files
2. Check the log file for the last successful download
3. Failed downloads will be listed in the summary

## Document Sources

The program downloads from official NVIDIA documentation sources:
- NVIDIA Documentation Portal (docs.nvidia.com)
- NVIDIA Enterprise Support (enterprise-support.nvidia.com)
- Partner documentation sites (Dell, Arrow, etc.)

## License

This program is provided as-is for educational and documentation purposes.

## Contributing

To add new documentation sources or improve the program:
1. Edit the `DOCUMENTS` dictionary in the `Config` class
2. Adjust rate limiting parameters if needed
3. Test thoroughly with a subset of documents first

## Support

For issues with the documentation content, please refer to the official NVIDIA documentation portal.

## Changelog

### Version 1.0
- Initial release
- Support for ConnectX, BlueField, Spectrum, MLNX_OFED, and Troubleshooting documentation
- Rate limiting and retry mechanisms
- Progress tracking and logging
- Organized directory structure