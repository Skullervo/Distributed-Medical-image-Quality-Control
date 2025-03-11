import grpc
from concurrent import futures
import analyze_service_pb2
import analyze_service_pb2_grpc
import fetch_service_pb2
import fetch_service_pb2_grpc
import psycopg2
import numpy as np
import io
import pydicom
from pydicom.errors import InvalidDicomError
from US_IQ_analysis3 import imageQualityUS
import os
import requests

#TODO ------> save all env variables from code to own file
# Orthanc ja Fetch Service adressess
ORTHANC_URL = os.getenv("ORTHANC_URL", "http://localhost:8042")
FETCH_SERVICE_ADDRESS = "localhost:50051"


# Database settings
DB_CONFIG = {
    "dbname": os.getenv("DATABASE_NAME", "QA-results"),
    "user": os.getenv("DATABASE_USER", "postgres"),
    "password": os.getenv("DATABASE_PASSWORD", "pohde24"),
    "host": os.getenv("DATABASE_HOST", "localhost"),
    "port": os.getenv("DATABASE_PORT", "5432"),
}

# Create DB connection and check that table is created
def connect_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ultrasound (
            id SERIAL PRIMARY KEY,
            institutionname TEXT,
            institutionaldepartmentname TEXT,
            manufacturer TEXT,
            modality TEXT,
            stationname TEXT,
            seriesdate TEXT,
            instance TEXT,
            serie TEXT,
            S_depth FLOAT,
            U_cov FLOAT,
            U_skew FLOAT,
            U_low FLOAT[]
        )
    """)
    conn.commit()
    cur.close()
    return conn

# Connect to fetch_service
def get_fetch_stub():
    options = [
        ("grpc.max_send_message_length", 200 * 1024 * 1024),
        ("grpc.max_receive_message_length", 200 * 1024 * 1024),
    ]
    channel = grpc.insecure_channel(FETCH_SERVICE_ADDRESS, options=options)
    return fetch_service_pb2_grpc.FetchServiceStub(channel)

class AnalyzeService(analyze_service_pb2_grpc.AnalyzeServiceServicer):
    def AnalyzeAllDicomData(self, request, context):
        print("📡 Received request to analyze all series in Orthanc")

        # Series from Orthanc
        response = requests.get(f"{ORTHANC_URL}/series")
        if response.status_code != 200:
            print("❌ Error: Could not fetch series from Orthanc")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return analyze_service_pb2.AnalyzeResponse(message="No series found", series_id="ALL")

        series_list = response.json()
        if not series_list:
            print("❌ No series found in Orthanc")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return analyze_service_pb2.AnalyzeResponse(message="No series available", series_id="ALL")

        fetch_stub = get_fetch_stub()
        conn = connect_db()
        cur = conn.cursor()

        for series_id in series_list:
            print(f"📡 Processing series ID: {series_id}")

            # Instances from Orthanc
            instance_response = requests.get(f"{ORTHANC_URL}/series/{series_id}/instances")
            if instance_response.status_code != 200:
                print(f"❌ Could not fetch instances for series {series_id}")
                continue  # skip

            instance_list = instance_response.json()
            if not instance_list:
                print(f"❌ No instances found for series {series_id}")
                continue  # skip

            for instance in instance_list:
                instance_id = instance["ID"]
                print(f"📡 Fetching instance ID: {instance_id}")

                # DICOM-data with Fetch-service
                fetch_response = fetch_stub.FetchDicomData(fetch_service_pb2.FetchRequest(instance_id=instance_id))

                if not fetch_response.dicom_data:
                    print(f"❌ No data received for instance {instance_id}")
                    continue  # skip

                # Monify binary data to DICOM format
                dicom_bytes = io.BytesIO(fetch_response.dicom_data)
                try:
                    dicom_dataset = pydicom.dcmread(dicom_bytes, force=True)
                    print("✅ DICOM data successfully read!")
                except InvalidDicomError as e:
                    print(f"❌ Error reading DICOM file: {e}")
                    continue  # Ohitetaan tämä instanssi

                # Metadata
                metadata = {
                    "InstitutionName": dicom_dataset.get("InstitutionName", "Unknown"),
                    "InstitutionalDepartmentName": dicom_dataset.get("InstitutionalDepartmentName", "Unknown"),
                    "Manufacturer": dicom_dataset.get("Manufacturer", "Unknown"),
                    "Modality": dicom_dataset.get("Modality", "Unknown"),
                    "StationName": dicom_dataset.get("StationName", "Unknown"),
                    "SeriesDate": dicom_dataset.get("SeriesDate", "Unknown")
                }

                if metadata["Modality"] != "US":
                    print("❌ Not an ultrasound image. Skipping...")
                    continue  # skip

                # Analyse image
                image_array = dicom_dataset.pixel_array
                analysis = imageQualityUS(dicom_dataset, dicom_bytes, image_array, "probe-LUT.xls")
                result = analysis.MAIN_US_analysis()

                # Modify results to JSON
                json_result = {
                    key: float(value) if isinstance(value, np.float64)
                    else value.tolist() if isinstance(value, np.ndarray)
                    else value for key, value in result.items()
                }

                # Save results to DB
                cur.execute("""
                    INSERT INTO ultrasound (
                        institutionname, institutionaldepartmentname, manufacturer, modality, 
                        stationname, seriesdate, instance, serie, S_depth, U_cov, U_skew, U_low
                    ) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    metadata["InstitutionName"],
                    metadata["InstitutionalDepartmentName"],
                    metadata["Manufacturer"],
                    metadata["Modality"],
                    metadata["StationName"],
                    metadata["SeriesDate"],
                    instance_id,
                    series_id,
                    float(json_result['S_depth']),
                    float(json_result['U_cov']),
                    float(json_result['U_skew']),
                    [float(val) for val in json_result['U_low']]
                ))

        conn.commit()
        cur.close()
        conn.close()

        return analyze_service_pb2.AnalyzeResponse(message="Analysis complete for all series!", series_id="ALL")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    analyze_service_pb2_grpc.add_AnalyzeServiceServicer_to_server(AnalyzeService(), server)
    server.add_insecure_port("[::]:50052")
    server.start()
    print("🚀 Analyze Service running on port 50052")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()


