import numpy as np
import pandas as pd
import json
import socket
import threading
import time
from io import StringIO
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.linear_model import Ridge
import base64
import os
import joblib
from datetime import datetime
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error


# ---------------- Trainer ----------------
class EmgTrainer:
    """Unified EMG Trainer for Ridge and MLP models."""

    def __init__(self, raw_emg_data, server=None, addr=None):
        self.raw_emg_data = raw_emg_data
        self.server = server  
        self.addr = addr      



        
    # ---------------- Preprocessing ----------------

    def preprocess(self, window_size=60, features=("rms", "mav")):
        """
        Extract features from raw EMG using a sliding window.
        features = tuple/list of feature types ("rms", "mav")..
        """
        X_features, y_labels = [], []
        for i in range(len(self.raw_emg_data) - window_size + 1):
            window = self.raw_emg_data[i:i+window_size]
            rectified = np.abs(window)
            feat_vector = []

            if "rms" in features:
                rms = np.sqrt(np.mean(rectified**2, axis=0))
                feat_vector.extend(rms)

            if "mav" in features:
                mav = np.mean(rectified, axis=0)
                feat_vector.extend(mav)

            if "var" in features:
                var = np.var(rectified, axis=0)
                feat_vector.extend(var)
            if "wl" in features:
                wl = np.sum(np.abs(np.diff(rectified, axis=0)), axis=0)
                feat_vector.extend(wl)

            if "zc" in features:
                threshold = 0.01
                zc = np.sum(((rectified[:-1] * rectified[1:]) < 0) & (np.abs(rectified[:-1] - rectified[1:]) >= threshold), axis=0)
                
                feat_vector.extend(zc)

            if "ssc" in features:
                threshold = 0.01
                ssc = np.sum(((rectified[1:-1] - rectified[0:-2]) * (rectified[1:-1] - rectified[2:]) > threshold), axis=0)
                feat_vector.extend(ssc)

            X_features.append(feat_vector)

        return np.array(X_features)
    
    # ---------------- Ridge ----------------


    def train_ridge_for_exo(self, X, y, alpha=1.0):
            # y is one-hot: [[1,0,0,0], [0,1,0,0], ...]
            y_class = np.array(y)

            X_train, X_test, y_train, y_test = train_test_split(X, y_class, test_size=0.2, random_state=42)

            models = []
            predictions = []
            for i in range(4):  # Train 4 separate models for each output
                model = Ridge(alpha=alpha)
                model.fit(X_train, y_train[:, i])
                models.append(model)
                predictions.append(model.predict(X_test))

            y_pred = np.column_stack(predictions)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)

            return {"models": models, "mse": mse, "mae": mae}

    def train_mlp_for_exo(self, X, y, save_tflite_path="mlp_model.tflite", epochs=50, batch_size=16):
        try:
            # Update model to output 4 values with softmax activation
            model = models.Sequential([
                layers.Input(shape=(X.shape[1],)),
                layers.Dense(64, activation='relu'),
                layers.Dense(32, activation='relu'),
                layers.Dense(4, activation='softmax')  # 4 outputs with softmax
            ])
            model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

            early_stop = tf.keras.callbacks.EarlyStopping(
                monitor='val_loss', patience=10, restore_best_weights=True
            )

            total_steps = int(np.ceil(len(X) / batch_size)) * epochs
            step_count = 0

            class ProgressCallback(tf.keras.callbacks.Callback):
                def on_batch_end(self, batch, logs=None):
                    nonlocal step_count
                    step_count += 1
                    progress_msg = f"TRAINING_PROGRESS {step_count}/{total_steps}"
                    try:
                        self.model_ref.server.socket.sendto(progress_msg.encode(), (self.model_ref.addr[0], self.model_ref.server.MODEL_SEND_PORT))
                    except Exception:
                        pass  # ignore send errors

            ProgressCallback.model_ref = self

            model.fit(
                X, y,
                validation_split=0.2,
                epochs=epochs,
                batch_size=batch_size,
                verbose=2,
                callbacks=[early_stop, ProgressCallback()]
            )

            converter = tf.lite.TFLiteConverter.from_keras_model(model)
            tflite_model = converter.convert()
            with open(save_tflite_path, "wb") as f:
                f.write(tflite_model)
            print(f"💾 MLP TFLite model saved to {save_tflite_path}")

            return model
        except Exception as e:
            self.server.send_error(self.addr, "train_mlp_for_exo", e)
            return None
    #change the feature set and window size as per need.
    def find_best_model(self, raw_emg, labels, model_type="RIDGE_FOR_EXO"):
        windows = [10, 25, 35, 45, 50, 55, 60]
        #feature_sets = [("rms",), ("mav",), ("rms", "mav"), ("rms", "mav", "var"), 
        #            ("rms", "mav", "var", "wl"), ("rms", "mav", "var", "wl", "zc"), 
        #            ("rms", "mav", "var", "wl", "zc", "ssc")]
       # feature_sets = [("rms",), ("mav",), ("rms", "mav") , ("rms", "mav", "var")]
        feature_sets = [("rms",)]
        best_mse = float('inf')
        best_model = None
        best_params = {}
        
        total_iterations = len(windows) * len(feature_sets)
        iteration_count = 0

        for window_size in windows:
            for features in feature_sets:
                try:
                    X = self.preprocess(window_size=window_size, features=features)
                    y_proc = labels[:X.shape[0]]
                    
                    if len(y_proc) == 0:
                        continue
                        
                    if model_type == "RIDGE_FOR_EXO":
                        result = self.train_ridge_for_exo(X, y_proc, alpha=1.0)
                    elif model_type == "TFLITE":
                        result = self.train_mlp_for_exo(X, y_proc)
                    else:
                        continue
                    
                    if result["mse"] < best_mse:
                        best_mse = result["mse"]
                        best_model = result
                        best_params = {
                            "window_size": window_size,
                            "features": features,
                            "mse": result["mse"],
                            "mae": result["mae"]
                        }
                    
                    print(f"Trained {model_type} with window={window_size}, features={features}, MSE={result['mse']:.4f}")

                    iteration_count += 1
                    progress_msg = f"TRAINING_PROGRESS {iteration_count}/{total_iterations}"
                    try:
                        self.server.socket.sendto(progress_msg.encode(), (self.addr[0], self.server.MODEL_SEND_PORT))
                    except Exception as e:
                        print(f" Failed to send {model_type} progress: {e}")
                        
                except Exception as e:
                    self.server.send_error(self.addr, f"Finding best {model_type} model: ", e)
                    print(f"Error with window={window_size}, features={features}: {e}")
                    continue
        
        return best_model, best_params


# ---------------- UDP Server ----------------
class UdpTrainingServer:
    MODEL_SEND_PORT = 12347
    CHUNK_TIMEOUT = 100

    def __init__(self, host='0.0.0.0', port=12346):
        try:
            self.host = host
            self.port = port
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((host, port))
            self.running = False
            self.data_chunks = {}
            self.chunk_timestamps = {}
            self.training_locks = {}  # Add this line
            print(f"Initialized UDP Training Server on {host}:{port}")
        except Exception as e:
            print(f" Error initializing server: {e}")



    def send_error(self, addr, stage, exc):
        """Send structured error to Android client."""
        try:
            error_msg = f"SERVER_ERROR:{stage}: {exc}"
            self.socket.sendto(error_msg.encode(), (addr[0], self.MODEL_SEND_PORT))
        except Exception as e:
            print(f" Failed to send error to {addr} at stage {stage}: {e}")


    def start(self):
        try:
            self.running = True
            print(f"🚀 UDP Server started on {self.host}:{self.port}")
            threading.Thread(target=self.cleanup_stale_chunks, daemon=True).start()
            while self.running:
                try:
                    data, addr = self.socket.recvfrom(65507)
                    threading.Thread(target=self.handle_data, args=(data, addr), daemon=True).start()
                except Exception as e:
                    if self.running:
                        print(f"⚠️ Error receiving data: {e}")
        except Exception as e:

            print(f" Server start failed: {e}")

    def stop(self):
        try:
            self.running = False
            self.socket.close()
            print(" Server stopped")
        except Exception as e:
            print(f" Error stopping server: {e}")



    def cleanup_stale_chunks(self):
        try:
            while self.running:
                now = time.time()
                stale_addrs = []
                for addr in list(self.chunk_timestamps.keys()):
                    try:
                        # Check if address still exists in data_chunks before processing
                        if addr not in self.data_chunks:
                            # Remove from timestamps if no longer in data_chunks
                            self.chunk_timestamps.pop(addr, None)
                            continue

                        elapsed = now - self.chunk_timestamps[addr]
                        if elapsed > self.CHUNK_TIMEOUT:
                            # Instead of dropping, ask client to resend missing chunks
                            self.request_missing_chunks(addr)
                            print(f"⏰ Requested missing chunks from {addr}")
                            # If still stale after second timeout, drop completely
                            if elapsed > self.CHUNK_TIMEOUT * 2:
                                stale_addrs.append(addr)

                    except Exception as e:
                        self.send_error(addr, "cleanup_stale_chunks", e)
                        print(f"Error checking timeout for {addr}: {e}")
                
                for addr in stale_addrs:
                    print(f" Timeout: Dropping session from {addr}")
                    self.data_chunks.pop(addr, None)
                    self.chunk_timestamps.pop(addr, None)
                
                time.sleep(5)                        
        except Exception as e:
            
            for addr in list(self.chunk_timestamps.keys()):
                try:
                    self.send_error(addr, "cleanup_stale_chunks_fatal", e)
                except Exception as inner:
                    print(f" Failed to send fatal cleanup_stale_chunks error to {addr}: {inner}")

            print(f" Error in cleanup_stale_chunks loop: {e}")


    def handle_data(self, data, addr):
        try:
            # --- If header packet (text) ---
            try:
                data_str = data.decode('utf-8')
                if data_str.startswith("MODEL_TYPE:"):
                    # Clear any existing data for this client
                    if addr in self.data_chunks:
                        del self.data_chunks[addr]
                    if addr in self.chunk_timestamps:
                        del self.chunk_timestamps[addr]
                    lines = data_str.splitlines()
                    model_type = lines[0].split(":")[1].strip().upper()
                    total_chunks = int(lines[1].split(":")[1])
                    print(f"📡 Header received from {addr}: model_type={model_type}, total_chunks={total_chunks}")
                    self.data_chunks[addr] = {"chunks": {}, "total": total_chunks, "model_type": model_type}
                    self.chunk_timestamps[addr] = time.time()
                    
                    # --- Send HEADER_ACK ---
                    try:
                        self.socket.sendto("HEADER_ACK".encode(), addr)
                        print(f"✅ HEADER_ACK sent to {addr}")
                    except Exception as e:
                        print(f"❌ Failed to send HEADER_ACK to {addr}: {e}")
                    return
            except UnicodeDecodeError:
                pass  # binary chunk, not header

            # --- If chunk packet ---
            if addr not in self.data_chunks:
                print(f"⚠️ Chunk received before header from {addr}")
                return

            header = data[:8]
            chunk_index = int.from_bytes(header[:4], 'big')
            total_chunks = int.from_bytes(header[4:8], 'big')
            chunk_data = data[8:]

            self.data_chunks[addr]["chunks"][chunk_index] = chunk_data
            self.chunk_timestamps[addr] = time.time()
            self.socket.sendto(f"ACK:{chunk_index}".encode(), addr)
            print(f"✅ ACK sent for chunk {chunk_index} to {addr}")

            # --- Check if all chunks received ---
            if len(self.data_chunks[addr]["chunks"]) == self.data_chunks[addr]["total"]:
                assembled_data = b''.join(self.data_chunks[addr]["chunks"][i] for i in range(total_chunks))
                csv_str = assembled_data.decode('utf-8')
                model_type = self.data_chunks[addr]["model_type"]
                del self.data_chunks[addr]
                
                # Send final ACK for Step D
                self.socket.sendto("ALL_CHUNKS_RECEIVED".encode(), addr)
    
                # Call training
                threading.Thread(target=self.train_and_send_models, args=(csv_str, addr, model_type), daemon=True).start()

        except Exception as e:
            self.send_error(addr, "handle_data", e)
            print(f"❌ Error in handle_data: {e}")



    def request_missing_chunks(self, addr):
        try:
            if addr not in self.data_chunks:
                return
            total = self.data_chunks[addr]["total"]
            received = self.data_chunks[addr]["chunks"]
            for i in range(total):
                if i not in received:
                    self.socket.sendto(f"RESEND:{i}".encode(), addr)
                    print(f"🔄 Requested resend for chunk {i} from {addr}")
        except Exception as e:
            self.send_error(addr, "request_missing_chunks", e)


    def send_file_udp(self, file_path, addr, chunk_size=60000):
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            total_chunks = (len(data) + chunk_size - 1) // chunk_size
            print(f"📤 Sending {file_path} ({len(data)} bytes, {total_chunks} chunks) to {addr}")

            for i in range(total_chunks):
                start = i * chunk_size
                end = start + chunk_size
                chunk_data = data[start:end]

                # Encode the chunk as Base64 string
                chunk_base64 = base64.b64encode(chunk_data).decode('utf-8')
                packet_str = f"MLP_TFLITE_CHUNK:{i}:{total_chunks}:{chunk_base64}"
                self.socket.sendto(packet_str.encode('utf-8'), (addr[0], self.MODEL_SEND_PORT))

                print(f" Sent chunk {i+1}/{total_chunks} for {file_path} to {addr}")
        except Exception as e:
            self.send_error(addr, "send_file_udp", e)
            print(f" Error sending file {file_path} to {addr}: {e}")


    def train_and_send_models(self, csv_str, addr, model_type):
            if addr not in self.training_locks:
                self.training_locks[addr] = threading.Lock()
                
            with self.training_locks[addr]:    
                try:
                    print(f" Training {model_type} model for {addr}...")
                    df = pd.read_csv(StringIO(csv_str))
                    raw_emg = df.iloc[:, :-4].values  # First 8 columns are EMG data
                    labels = df.iloc[:, -4:].values   # Last 4 columns are one-hot labels

                    trainer = EmgTrainer(raw_emg, server=self, addr=addr)
                    
                    if model_type == "RIDGE_FOR_EXO":
                        best_model, best_params = trainer.find_best_model(raw_emg, labels, "RIDGE_FOR_EXO")
                        
                        
                        models_list = []
                        output_names = ["isometric", "extension", "flexion", "rest"]
                        
                        for i, output_name in enumerate(output_names):
                            models_list.append({
                                "name": output_name,
                                "intercept": best_model["models"][i].intercept_,
                                "coef": best_model["models"][i].coef_.tolist()
                            })
                        
                        ridge_exo_json = {
                            "type": "RIDGE_FOR_EXO",
                            "models": models_list,
                            "preprocessing": best_params
                        }
                        self.socket.sendto(json.dumps(ridge_exo_json).encode(), (addr[0], self.MODEL_SEND_PORT))

                    elif model_type == "TFLITE":
                        # Use default preprocessing for MLP
                        X = trainer.preprocess()
                        y_proc = labels[:X.shape[0]]
                        mlp_path = "mlp_model.tflite"
                        trainer.train_mlp_for_exo(X, y_proc, save_tflite_path=mlp_path)
                        self.send_file_udp(mlp_path, addr)

                    print(f" {model_type} training complete for {addr}")

                except Exception as e:
                    self.send_error(addr, "train_and_send_models", e)
                    print(f" Training error: {e}")
                finally:
                    if addr in self.training_locks:
                        del self.training_locks[addr]


LOG_FILE = "ridge_experiments_log.json"

def log_experiment(window_size, features, mse, mae, model_file):
    """
    Log a Ridge training experiment to a JSON file.
    Each entry contains preprocessing, metrics, timestamp, and model file.
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "window_size": window_size,
        "features": features,
        "mse": mse,
        "mae": mae,
        "model_file": model_file
    }

    # Load existing log if it exists
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                log_data = json.load(f)
            except json.JSONDecodeError:
                log_data = []
    else:
        log_data = []

    # Append new entry and save
    log_data.append(log_entry)
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=4)

    print(f" Logged experiment: {model_file}")

import itertools

def start_standalone_training(csv_path):
    """Train Ridge models locally from CSV, log experiments, and show results."""
    try:
        print(f"📂 Training from local file: {csv_path}")
        df = pd.read_csv(csv_path)
        raw_emg = df.iloc[:, :-1].values
        labels = pd.to_numeric(df.iloc[:, -1], errors="coerce").astype(float)

        # --- Generate all possible non-empty feature combinations ---
        all_features = ["rms", "mav", "var", "wl", "zc", "ssc"]
        
        feature_sets = []
        for r in range(1, len(all_features)+1):
            combos = itertools.combinations(all_features, r)
            feature_sets.extend(combos)
        feature_sets = [tuple(f) for f in feature_sets]  # ensure tuples

        # --- Window sizes ---
        windows = [10, 15, 20, 25, 30, 50, 60, 100]

        # --- Experiments: all combinations of windows and feature sets ---
        experiments = [{"window_size": w, "features": f} for w in windows for f in feature_sets]

        all_results = []

        for exp in experiments:
            trainer = EmgTrainer(raw_emg)
            X = trainer.preprocess(window_size=exp["window_size"], features=exp["features"])
            y_proc = labels[:X.shape[0]]  # align labels

            model, mse, mae = trainer.train_ridge(X, y_proc, alpha=1.0)

            model_file = f"ridge_ws{exp['window_size']}_{'+'.join(exp['features'])}.pkl"
            joblib.dump(model, model_file)

            log_experiment(exp["window_size"], exp["features"], mse, mae, model_file)

            all_results.append({
                "window_size": exp["window_size"],
                "features": exp["features"],
                "mse": mse,
                "mae": mae,
                "model_file": model_file
            })
            print(f" Trained Ridge with {exp}, MSE={mse:.4f}, MAE={mae:.4f}")

        # ---------------- Show all results ----------------
        print("\n All Experiments:")
        print(f"{'Window':>6} | {'Features':>25} | {'MSE':>10} | {'MAE':>10} | {'Model File':>30}")
        print("-"*90)
        best_mse = float('inf')
        best_model = None
        for res in all_results:
            features_str = "+".join(res["features"])
            print(f"{res['window_size']:>6} | {features_str:>25} | {res['mse']:>10.4f} | {res['mae']:>10.4f} | {res['model_file']:>30}")
            if res["mse"] < best_mse:
                best_mse = res["mse"]
                best_model = res

        print("\n Best model based on lowest MSE:")
        print(f"Window: {best_model['window_size']}, Features: {best_model['features']}, MSE: {best_model['mse']:.4f}, MAE: {best_model['mae']:.4f}, File: {best_model['model_file']}")

    except Exception as e:
        print(f" Error in start_standalone_training: {e}")




# ---------------- Main ----------------
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='EMG Model Trainer')
    parser.add_argument('--mode', choices=['server', 'train'], default='server',
                        help='Run as server or train from local file')
    parser.add_argument('--csv', help='Path to CSV file for training')
    parser.add_argument('--host', default='0.0.0.0', help='Host for server mode')
    parser.add_argument('--port', type=int, default=12346, help='Port for server mode')
    
    args = parser.parse_args()
    
    if args.mode == 'server':
        # Start UDP server
        server = UdpTrainingServer(host=args.host, port=args.port)
        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()
        except Exception as e:
            print(f" Fatal server error: {e}")
    else:
        # Train from local file
        if not args.csv:
            print("Please specify a CSV file with --csv argument")
            exit(1)
        start_standalone_training(args.csv)
