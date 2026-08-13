#!/usr/bin/env python3
"""
Generate test data for Roomzin quick-start

Usage:
  python3 gen_data.py --shards 2
  python3 gen_data.py --shards 3 --days 7
"""

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Hardcoded values
SEGMENTS_PER_SHARD = 4
PROPERTIES_PER_SEGMENT = 10
ROOM_TYPES_PER_PROPERTY = 4
DEFAULT_DAYS = 10

# Static data
PROPERTY_TYPES = ["hotel", "hostel", "resort", "apartment"]
CATEGORIES = ["budget", "standard", "premium", "luxury"]
AMENITIES = ["wifi", "pool", "breakfast", "spa", "restaurant", "bar", "gym", "parking"]
RATE_FEATURES = [
    "free_cancellation",
    "non_refundable",
    "pay_at_property",
    "includes_breakfast",
    "free_wifi",
    "no_prepayment",
    "partial_refund",
    "instant_confirmation",
]

def generate_properties(shard_idx, segments, props_per_seg, output_dir):
    """Generate properties.csv for a shard"""
    
    properties = []
    
    for seg_idx, segment in enumerate(segments, 1):
        area = f"area_{shard_idx}_{seg_idx}"
        base_lat = 40.0 + shard_idx * 0.5 + seg_idx * 0.1
        base_lon = -74.0 + shard_idx * 0.5 + seg_idx * 0.1
        
        for prop_idx in range(1, props_per_seg + 1):
            prop_id = f"s{shard_idx}_seg{seg_idx}_p{prop_idx}"
            
            stars = random.randint(2, 5)
            prop_type = random.choice(PROPERTY_TYPES)
            category = random.choice(CATEGORIES)
            
            lat = base_lat + random.uniform(-0.01, 0.01)
            lon = base_lon + random.uniform(-0.01, 0.01)
            
            num_amenities = random.randint(3, 5)
            amenity_list = random.sample(AMENITIES, min(num_amenities, len(AMENITIES)))
            amenity_str = "|".join(amenity_list)
            
            properties.append({
                "PropertyID": prop_id,
                "Segment": segment,
                "Area": area,
                "PropertyType": prop_type,
                "Category": category,
                "Stars": stars,
                "Latitude": f"{lat:.6f}",
                "Longitude": f"{lon:.6f}",
                "Amenities": amenity_str,
            })
    
    csv_path = output_dir / "properties.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=properties[0].keys())
        writer.writeheader()
        writer.writerows(properties)
    
    return properties

def generate_packages(properties, room_types, days, output_dir):
    """Generate packages.csv for a shard"""
    
    packages = []
    today = datetime.now().date()
    
    for prop in properties:
        prop_id = prop["PropertyID"]
        
        for room_idx in range(1, room_types + 1):
            room_type = f"room{room_idx}"
            base_price = random.randint(50, 300)
            
            num_features = random.randint(1, 3)
            features = random.sample(RATE_FEATURES, min(num_features, len(RATE_FEATURES)))
            rate_feature = "|".join(features)
            
            for day_offset in range(days):
                date = today + timedelta(days=day_offset)
                date_str = date.strftime("%Y-%m-%d")
                
                avail = random.randint(1, 20)
                price = base_price + (day_offset % 3) * 10
                if date.weekday() >= 5:
                    price = int(price * 1.2)
                
                packages.append({
                    "PropertyID": prop_id,
                    "RoomType": room_type,
                    "Date": date_str,
                    "Availability": avail,
                    "FinalPrice": price,
                    "RateFeature": rate_feature,
                })
    
    csv_path = output_dir / "packages.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=packages[0].keys())
        writer.writeheader()
        writer.writerows(packages)
    
    return packages

def generate_shard_data(shard_idx, num_segments, props_per_seg, room_types, days, output_dir):
    """Generate all data for a single shard"""
    
    shard_id = f"shard{shard_idx}"
    shard_dir = output_dir / shard_id
    shard_dir.mkdir(parents=True, exist_ok=True)
    
    start_seg = (shard_idx - 1) * num_segments + 1
    segments = [f"segment_{i}" for i in range(start_seg, start_seg + num_segments)]
    
    properties = generate_properties(shard_idx, segments, props_per_seg, shard_dir)
    packages = generate_packages(properties, room_types, days, shard_dir)
    
    return shard_id, len(properties), len(packages)

def main():
    parser = argparse.ArgumentParser(description="Generate test data for Roomzin")
    parser.add_argument("--shards", type=int, default=2, help="Number of shards (default: 2)")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help=f"Days of availability (default: {DEFAULT_DAYS})")
    parser.add_argument("--output", type=str, default="./test-data", help="Output directory (default: ./test-data)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing test-data")
    args = parser.parse_args()
    
    if args.shards < 1:
        print("❌ Error: --shards must be >= 1")
        return
    
    output_dir = Path(args.output)
    if output_dir.exists() and not args.force:
        print(f"❌ Error: {output_dir} exists. Use --force to overwrite.")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Generating test data...")
    print(f"   Shards: {args.shards}")
    print(f"   Segments per shard: {SEGMENTS_PER_SHARD}")
    print(f"   Properties per segment: {PROPERTIES_PER_SEGMENT}")
    print(f"   Room types per property: {ROOM_TYPES_PER_PROPERTY}")
    print(f"   Days: {args.days}")
    print(f"   Output: {output_dir}")
    print()
    
    total_props = 0
    total_pkgs = 0
    shard_ids = []
    
    for shard_idx in range(1, args.shards + 1):
        shard_id, props, pkgs = generate_shard_data(
            shard_idx,
            SEGMENTS_PER_SHARD,
            PROPERTIES_PER_SEGMENT,
            ROOM_TYPES_PER_PROPERTY,
            args.days,
            output_dir
        )
        shard_ids.append(shard_id)
        total_props += props
        total_pkgs += pkgs
        print(f"  ✓ {shard_id}: {props} properties, {pkgs} packages")
    
    print()
    print(f"✅ Data generated:")
    print(f"   Total properties: {total_props}")
    print(f"   Total packages: {total_pkgs}")
    print(f"   Output: {output_dir}")
    print(f"   Shards: {', '.join(shard_ids)}")

if __name__ == "__main__":
    main()