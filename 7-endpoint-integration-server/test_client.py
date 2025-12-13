import requests

def test_medical_report_analysis():
    """
    Test function to demonstrate how to send a medical report image to the server
    """
    url = "http://localhost:80/analyze_medical_report"
    
    # Replace with the path to an actual medical report image
    # Use absolute path or path relative to script location
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, "..", "6-fine-tuning-vl", "test-img", "scan_item10-_71.jpg")
    
    try:
        with open(image_path, 'rb') as image_file:
            files = {'image': image_file}
            response = requests.post(url, files=files)
            
        if response.status_code == 200:
            result = response.json()
            print("Analysis Result:")
            print(result["analysis_result"])
            print("\nHealth Recommendations:")
            print(result["health_recommendations"])
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
    except FileNotFoundError:
        print(f"Image file {image_path} not found. Please provide a valid image path.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    test_medical_report_analysis()