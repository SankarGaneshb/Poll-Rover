import json
import os
import sys

def check_data_health(geojson_path):
    print(f"🔍 Auditing Data Health: {geojson_path}")
    
    if not os.path.exists(geojson_path):
        print("❌ Error: stations.geojson not found!")
        return False

    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        features = data.get('features', [])
        count = len(features)
        
        if count == 0:
            print("⚠️ Warning: No stations found in data!")
            return False

        # Basic attribute check
        integrity_score = 0
        for f in features:
            props = f.get('properties', {})
            if props.get('name') and props.get('address') and props.get('state'):
                integrity_score += 1
        
        health_pct = (integrity_score / count) * 100
        print(f"✅ Harvest Health: {health_pct:.1f}% ({integrity_score}/{count} valid stations)")
        
        if health_pct < 80:
            print("⚠️ ALERT: Data quality dropped below threshold!")
            return False
            
        return True

    except Exception as e:
        print(f"❌ Critical Error during audit: {str(e)}")
        return False

if __name__ == "__main__":
    path = os.path.join("static", "data", "stations.geojson")
    success = check_data_health(path)
    sys.exit(0 if success else 1)
