from django.shortcuts import render,redirect,get_object_or_404
from django.http.response import HttpResponseRedirect,HttpResponse
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import DataFileUpload
def base(request):
    return render(request,'homeApp/landing_page.html')
    
def upload_credit_data(request):
    return render(request,'homeApp/upload_credit_data.html')
def prediction_button(request):
    return render(request,'homeApp/fraud_detection.html')
    
def reports(request):
    all_data_files_objs=DataFileUpload.objects.all()
    return render(request,'homeApp/reports.html',{'all_files':all_data_files_objs})
    
def enter_form_data_manually(request):
    return render(request,'homeApp/enter_form_data_manually.html')
def predict_data_manually(request):
    return render(request,'homeApp/predict_data_manually.html')

def add_files_single(request):
    return render(request,'homeApp/add_files_single.html')
def predict_csv_single(request):
    return render(request,'homeApp/predict_csv_single.html')

def add_files_multi(request):
    return render(request,'homeApp/add_files_multi.html')
    
def predict_csv_multi(request):
    return render(request,'homeApp/predict_csv_multi.html')

def account_details(request):
    return render(request,'homeApp/account_details.html')
def change_password(request):
    return render(request,'homeApp/change_password.html')
def analysis(request):
    return render(request,'homeApp/analysis.html')
def view_data(request):
    return render(request,'homeApp/view_data.html')
def delete_data(request,id):
    obj=DataFileUpload.objects.get(id=id)
    obj.delete()
    messages.success(request, "File Deleted succesfully",extra_tags = 'alert alert-success alert-dismissible show')
    return HttpResponseRedirect('/reports')
def upload_data(request):
    if request.method == 'POST':
            data_file_name  = request.POST.get('data_file_name')
            try:
                actual_file = request.FILES['actual_file_name']
                
            except:
                messages.warning(request, "Invalid/wrong format. Please upload File.")
                return redirect('/upload_credit_data')
            description  = request.POST.get('description')

            DataFileUpload.objects.create(
                        file_name=data_file_name,
                        actual_file=actual_file,
                        description=description,
                        
                    )
            messages.success(request, "File Uploaded succesfully",extra_tags = 'alert alert-success alert-dismissible show')
            return HttpResponseRedirect('/reports')
    # return HttpResponseRedirect('reports')
    

def userLogout(request):
    try:
      del request.session['username']
    except:
      pass
    logout(request)
    return HttpResponseRedirect('/') 
    

def login2(request):
    data = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        print(user)
        if user:
            login(request, user)
            return HttpResponseRedirect('/')
        
        else:    
            data['error'] = "Username or Password is incorrect"
            res = render(request, 'homeApp/login.html', data)
            return res
    else:
        return render(request, 'homeApp/login.html', data)


def about(request):
    return render(request,'homeApp/about.html')

def dashboard(request):
    return render(request,'homeApp/dashboard.html')


import pandas as pd
import os
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

DATA_PATH = os.path.join(settings.BASE_DIR, 'all_data.csv')

# Define meaningful column names for credit card features
COLUMN_MAPPING = {
    'V1': 'time_delta',
    'V2': 'amount_normalized', 
    'V3': 'transaction_frequency',
    'V4': 'location_variance',
    'V5': 'merchant_category',
    'V6': 'device_type',
    'V7': 'transaction_type',
    'V8': 'card_present',
    'V9': 'day_of_week',
    'V10': 'hour_of_day',
    'V11': 'distance_from_home',
    'V12': 'international',
    'V13': 'online_purchase',
    'V14': 'velocity_24h',
    'V15': 'velocity_1week',
    'V16': 'customer_age',
    'V17': 'repeat_merchant',
    'V18': 'high_risk_merchant',
    'V19': 'previous_fraud_merchant',
    'V20': 'card_age_days',
    'V21': 'customer_tenure',
    'V22': 'avg_transaction_value',
    'V23': 'purchase_frequency',
    'V24': 'decline_rate',
    'V25': 'payment_method',
    'V26': 'authentication_method',
    'V27': 'ip_risk_score',
    'V28': 'browser_fingerprint'
}

def rename_columns(df):
    """Rename columns using the defined mapping"""
    rename_dict = {col: COLUMN_MAPPING.get(col, col) for col in df.columns if col in COLUMN_MAPPING}
    return df.rename(columns=rename_dict)

def extract_transaction_features(df):
    """Extract additional features from existing ones"""
    # Create a copy to avoid modifying the original if passed by reference
    df = df.copy()
    
    # Calculate transaction velocity (rate of spending)
    if 'Amount' in df.columns and 'Time' in df.columns:
        df['spending_rate'] = df['Amount'] / (df['Time'] + 1)  # Avoid division by zero
    
    # Create feature for unusual amount relative to customer history
    if 'amount_normalized' in df.columns and 'avg_transaction_value' in df.columns:
        df['amount_deviation'] = abs(df['amount_normalized'] - df['avg_transaction_value'])
    
    # Flag transactions occurring at unusual hours (if hour data available)
    if 'hour_of_day' in df.columns:
        df['unusual_hour'] = ((df['hour_of_day'] > 1) & (df['hour_of_day'] < 5)).astype(float)
    
    # Interaction features often reveal patterns
    if set(['international', 'high_risk_merchant']).issubset(df.columns):
        df['intl_high_risk'] = df['international'] * df['high_risk_merchant']
    
    # Add transaction timing risk score (higher for overnight and weekend transactions)
    if 'hour_of_day' in df.columns and 'day_of_week' in df.columns:
        # Weekend transactions (day_of_week 5-6 = Saturday-Sunday)
        is_weekend = ((df['day_of_week'] >= 5) & (df['day_of_week'] <= 6)).astype(float)
        
        # Night transactions (11pm - 5am)
        is_night = ((df['hour_of_day'] >= 23) | (df['hour_of_day'] <= 5)).astype(float)
        
        # Combined timing risk score
        df['timing_risk'] = is_weekend * 0.5 + is_night * 0.5
    
    # High-value transaction flag
    if 'Amount' in df.columns:
        # Transactions over $1000 or in 95th percentile
        threshold = max(1000, df['Amount'].quantile(0.95))
        df['high_value_transaction'] = (df['Amount'] > threshold).astype(float)
    
    # Velocity ratios
    if 'velocity_24h' in df.columns and 'velocity_1week' in df.columns:
        # High daily velocity relative to weekly pattern
        df['velocity_ratio'] = df['velocity_24h'] / (df['velocity_1week'] / 7 + 0.001)
    
    # Distance and merchant risk combined
    if 'distance_from_home' in df.columns and 'high_risk_merchant' in df.columns:
        # Risky if both far from home and at high risk merchant
        df['distance_merchant_risk'] = (
            (df['distance_from_home'] > df['distance_from_home'].quantile(0.8)) & 
            (df['high_risk_merchant'] == 1)
        ).astype(float)
    
    return df

def transform_input_data(df):
    """Transform input data to align with column semantics"""
    # Create a copy to avoid modifying the original
    transformed_df = df.copy()
    
    # Only apply transformations if we have the original V columns
    v_columns = [f'V{i}' for i in range(1, 29)]
    if not any(col in df.columns for col in v_columns):
        # Data is already transformed or doesn't have V columns
        return df
    
    # Store original Class and Amount columns if they exist
    class_col = df['Class'].copy() if 'Class' in df.columns else None
    amount_col = df['Amount'].copy() if 'Amount' in df.columns else None
    
    # Transform and scale features to match their semantic meaning
    
    # 1. Time-related features
    if 'V1' in df.columns:  # time_delta
        # Scale to represent hours since last transaction (0-72 hours)
        transformed_df['time_delta'] = ((df['V1'] - df['V1'].min()) / 
                                      (df['V1'].max() - df['V1'].min() + 1e-10) * 72)
    
    if 'V9' in df.columns:  # day_of_week
        # Scale to 0-6 (Monday to Sunday)
        transformed_df['day_of_week'] = ((df['V9'] - df['V9'].min()) / 
                                       (df['V9'].max() - df['V9'].min() + 1e-10) * 6).round()
    
    if 'V10' in df.columns:  # hour_of_day
        # Scale to 0-23 (hours of day)
        transformed_df['hour_of_day'] = ((df['V10'] - df['V10'].min()) / 
                                       (df['V10'].max() - df['V10'].min() + 1e-10) * 23).round()
    
    # 2. Amount-related features
    if 'V2' in df.columns:  # amount_normalized
        # Use the actual Amount column if available, otherwise derive from V2
        if amount_col is not None:
            transformed_df['amount_normalized'] = (amount_col - amount_col.mean()) / (amount_col.std() + 1e-10)
        else:
            transformed_df['amount_normalized'] = df['V2']
    
    if 'V22' in df.columns:  # avg_transaction_value
        # Generate realistic average transaction values (50-1000)
        raw_values = df['V22']
        transformed_df['avg_transaction_value'] = 50 + ((raw_values - raw_values.min()) / 
                                                     (raw_values.max() - raw_values.min() + 1e-10) * 950)
    
    # 3. Boolean/categorical features (convert to 0/1 or categories)
    binary_features = {
        'V7': 'transaction_type',    # 0=in-person, 1=online
        'V8': 'card_present',        # 0=not present, 1=present
        'V12': 'international',      # 0=domestic, 1=international
        'V13': 'online_purchase',    # 0=in-store, 1=online
        'V17': 'repeat_merchant',    # 0=new merchant, 1=repeat
        'V18': 'high_risk_merchant'  # 0=normal, 1=high risk
    }
    
    for v_col, new_col in binary_features.items():
        if v_col in df.columns:
            # Convert to binary 0/1 based on median threshold
            median = df[v_col].median()
            transformed_df[new_col] = (df[v_col] > median).astype(int)
    
    # 4. Numeric range features (scale to appropriate ranges)
    range_features = {
        'V4': ('location_variance', 0, 100),          # 0-100 score
        'V5': ('merchant_category', 1, 20),           # 1-20 category code
        'V6': ('device_type', 1, 5),                  # 1-5 device type
        'V11': ('distance_from_home', 0, 1000),       # 0-1000 km
        'V14': ('velocity_24h', 0, 20),               # 0-20 transactions/day
        'V15': ('velocity_1week', 0, 50),             # 0-50 transactions/week
        'V16': ('customer_age', 18, 80),              # 18-80 years
        'V19': ('previous_fraud_merchant', 0, 1),     # 0-1 probability
        'V20': ('card_age_days', 1, 1095),            # 1-1095 days (3 years)
        'V21': ('customer_tenure', 1, 3650),          # 1-3650 days (10 years)
        'V23': ('purchase_frequency', 0, 30),         # 0-30 purchases/month
        'V24': ('decline_rate', 0, 0.5),              # 0-0.5 (50% declines)
        'V25': ('payment_method', 1, 5),              # 1-5 payment methods
        'V26': ('authentication_method', 1, 4),       # 1-4 auth methods
        'V27': ('ip_risk_score', 0, 1),               # 0-1 risk score
        'V28': ('browser_fingerprint', 0, 1)          # 0-1 uniqueness score
    }
    
    for v_col, (new_col, min_val, max_val) in range_features.items():
        if v_col in df.columns:
            # Scale to the specified range
            raw_values = df[v_col]
            if raw_values.max() > raw_values.min():  # Avoid division by zero
                transformed_df[new_col] = min_val + ((raw_values - raw_values.min()) / 
                                                  (raw_values.max() - raw_values.min() + 1e-10) * (max_val - min_val))
            else:
                transformed_df[new_col] = min_val
    
    # 5. Re-add Class column if it existed
    if class_col is not None:
        transformed_df['Class'] = class_col
    
    # 6. Re-add original Amount column if it existed
    if amount_col is not None:
        transformed_df['Amount'] = amount_col
    
    # Remove original V columns to avoid confusion
    for col in v_columns:
        if col in transformed_df.columns:
            transformed_df = transformed_df.drop(col, axis=1)
    
    return transformed_df

@csrf_exempt
def predict_fraud_csv(request):
    """
    View function to handle fraud detection from uploaded CSV files.
    - Processes uploaded CSV
    - Combines with historical data for training
    - Uses hybrid approach (Isolation Forest + RandomForest) to detect anomalies (fraud)
    - Persists results to the main data store
    """
    if request.method != 'POST' or not request.FILES.get('csv_file'):
        return HttpResponseBadRequest("Invalid request. Please upload a CSV file using POST.")
    
    print("View called")
    try:
        uploaded_file = request.FILES['csv_file']
        
        # Improved CSV parsing with error handling
        try:
            new_data = pd.read_csv(uploaded_file, skipinitialspace=True)
            if new_data.empty:
                return JsonResponse({"error": "Uploaded CSV is empty"})
            print(f"CSV loaded with shape {new_data.shape}")
            
            # Transform data to match column semantics (if original V columns exist)
            new_data = transform_input_data(new_data)
            
            # Rename any remaining V columns to meaningful names
            new_data = rename_columns(new_data)
            
        except Exception as e:
            return JsonResponse({"error": f"Error parsing CSV: {str(e)}"})
        
        # Initialize prediction columns if they don't exist
        for col in ['Prediction', 'Actual', 'Correct', 'Fraud_Probability']:
            if col not in new_data.columns:
                new_data[col] = None
        
        # Load historical data if it exists
        if os.path.exists(DATA_PATH):
            try:
                past_data = pd.read_csv(DATA_PATH)
                
                # If past data has original V columns, transform it
                past_data = transform_input_data(past_data)
                
                # Rename any remaining V columns in historical data
                past_data = rename_columns(past_data)
            except Exception as e:
                print(f"Error loading historical data: {str(e)}")
                # If file exists but can't be read, create a new DataFrame
                past_data = pd.DataFrame(columns=new_data.columns)
        else:
            past_data = pd.DataFrame(columns=new_data.columns)
        
        # Ensure past_data and new_data have the same columns before combining
        for col in new_data.columns:
            if col not in past_data.columns:
                past_data[col] = None
        
        for col in past_data.columns:
            if col not in new_data.columns:
                new_data[col] = None
        
        # Extract additional features
        new_data = extract_transaction_features(new_data)
        past_data = extract_transaction_features(past_data)
        
        # Combine datasets
        combined_data = pd.concat([past_data, new_data], ignore_index=True)
        
        # Select feature columns, excluding metadata and prediction columns
        non_features = ['Class', 'Prediction', 'Actual', 'Correct', 'Fraud_Probability']
        feature_cols = [col for col in combined_data.columns if col not in non_features]
        
        # Get only numeric columns for both datasets
        numeric_cols = combined_data[feature_cols].select_dtypes(include=['number']).columns.tolist()
        
        # Prepare the datasets
        X_combined = combined_data[numeric_cols].copy()
        
        # Fill missing values with median (more robust than mean)
        for col in numeric_cols:
            X_combined[col] = X_combined[col].fillna(X_combined[col].median() if not X_combined[col].empty else 0)
        
        # Scale the features - important for distance-based algorithms
        scaler = StandardScaler()
        X_combined_scaled = scaler.fit_transform(X_combined)
        X_combined_scaled = pd.DataFrame(X_combined_scaled, columns=numeric_cols)
        
        # APPROACH 1: Isolation Forest for Anomaly Detection
        # Dynamic contamination parameter
        contamination = 0.01  # Default baseline
        if 'Actual' in combined_data.columns and not combined_data['Actual'].isna().all():
            # If we have labeled data, estimate a better contamination value
            known_fraud_rate = (combined_data['Actual'] == 'Fraud').mean()
            if not np.isnan(known_fraud_rate) and known_fraud_rate > 0:
                # Set contamination slightly higher than observed fraud rate
                contamination = max(0.005, min(0.15, known_fraud_rate * 2))
                print(f" Estimated fraud rate: {known_fraud_rate:.4f}, setting contamination to {contamination:.4f}")
        
        iso_model = IsolationForest(
            n_estimators=200,  # More trees for stability
            max_samples='auto',
            contamination=contamination,
            max_features=0.8,  # Use subset of features for better generalization
            bootstrap=True,  # Enable bootstrapping for robust training
            n_jobs=-1,
            random_state=42,
            verbose=0
        )
        
        # Fit on scaled data for better performance
        iso_model.fit(X_combined_scaled)
        
        # APPROACH 2: Supervised learning if we have labeled data
        supervised_model = None
        if 'Class' in combined_data.columns and not combined_data['Class'].isna().all():
            try:
                # Extract labeled data
                y_combined = combined_data['Class'].astype(int)
                X_train, X_test, y_train, y_test = train_test_split(
                    X_combined_scaled, y_combined, test_size=0.2, random_state=42, stratify=y_combined
                )
                
                # Handle class imbalance with SMOTE
                # Only apply if we have enough samples of minority class
                if (y_train == 1).sum() >= 5:  # Need at least 5 fraud samples
                    smote = SMOTE(random_state=42, k_neighbors=min(5, (y_train == 1).sum() - 1))
                    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
                else:
                    # If not enough fraud samples, use class weights instead
                    X_train_resampled, y_train_resampled = X_train, y_train
                
                # Train a Random Forest Classifier
                supervised_model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=None,
                    min_samples_split=2,
                    min_samples_leaf=1,
                    max_features='sqrt',
                    class_weight='balanced',  # Handle imbalance
                    n_jobs=-1,
                    random_state=42
                )
                supervised_model.fit(X_train_resampled, y_train_resampled)
                
                print(f"Supervised model trained with {X_train_resampled.shape[0]} samples")
            except Exception as e:
                print(f"Could not train supervised model: {str(e)}")
                supervised_model = None
        
        # Process new data for prediction
        try:
            # Prepare new data for prediction
            X_new = new_data[numeric_cols].copy()
            
            # Fill missing values with the median from combined data
            for col in numeric_cols:
                if col in X_new.columns:
                    X_new[col] = X_new[col].fillna(X_combined[col].median() if not X_combined[col].empty else 0)
            
            # Scale new data using the same scaler
            X_new_scaled = scaler.transform(X_new)
            
        except KeyError as e:
            missing_cols = set(numeric_cols) - set(new_data.columns)
            return JsonResponse({
                "error": f"Missing required columns in new data: {', '.join(missing_cols)}. Please ensure the new data has the same structure as the training data."
            }, status=400)
        
        if X_new.empty or X_new.shape[1] == 0:
            return JsonResponse({"error": "No valid numeric features in new data for prediction"})
        
        # Make predictions using both models when available
        try:
            # Isolation Forest predictions (anomaly scores)
            iso_scores = iso_model.decision_function(X_new_scaled)
            iso_preds = iso_model.predict(X_new_scaled)
            
            # Convert to probabilities (higher negative score = more likely to be fraud)
            iso_probs = 1 - (iso_scores - iso_scores.min()) / (iso_scores.max() - iso_scores.min() + 1e-10)
            
            # If we have a supervised model, combine predictions
            if supervised_model:
                # Get probability estimates from Random Forest
                rf_probs = supervised_model.predict_proba(X_new_scaled)[:, 1]
                
                # Weighted ensemble (give more weight to supervised model if available)
                fraud_probs = 0.3 * iso_probs + 0.7 * rf_probs
                
                # Use a dynamic threshold based on the distribution of probabilities
                threshold = max(0.5, np.percentile(fraud_probs, 100 - contamination * 100))
                fraud_preds = (fraud_probs >= threshold).astype(int)
            else:
                # Use only Isolation Forest
                fraud_probs = iso_probs
                fraud_preds = (iso_preds == -1).astype(int)  # -1 is anomaly in Isolation Forest
            
            # Store predictions and probabilities
            new_data['Prediction'] = ['Fraud' if p == 1 else 'Normal' for p in fraud_preds]
            new_data['Fraud_Probability'] = fraud_probs
            
        except Exception as e:
            print(f"Error during prediction: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": f"Prediction error: {str(e)}"}, status=500)
        
        # Set actual values if Class column exists
        if 'Class' in new_data.columns:
            new_data['Actual'] = ['Fraud' if c == 1 else 'Normal' for c in new_data['Class']]
            new_data['Correct'] = new_data['Prediction'] == new_data['Actual']
        
        # Update dataset and save
        updated_data = pd.concat([past_data, new_data], ignore_index=True)
        try:
            updated_data.to_csv(DATA_PATH, index=False)
        except Exception as e:
            print(f"Warning: Could not save updated data: {str(e)}")
            # Continue processing even if saving fails
        
        # Calculate prediction metrics if actual values exist
        metrics = {}
        if 'Actual' in new_data.columns and not new_data['Actual'].isna().all():
            true_frauds = (new_data['Actual'] == 'Fraud').sum()
            detected_frauds = (new_data['Prediction'] == 'Fraud').sum()
            correct_frauds = ((new_data['Prediction'] == 'Fraud') & 
                            (new_data['Actual'] == 'Fraud')).sum()
            
            # Calculate F1 score components
            precision = correct_frauds / detected_frauds if detected_frauds > 0 else 0
            recall = correct_frauds / true_frauds if true_frauds > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            metrics = {
                "true_frauds": int(true_frauds),
                "detected_frauds": int(detected_frauds),
                "correct_frauds": int(correct_frauds),
                "detection_rate": float(correct_frauds / true_frauds) if true_frauds > 0 else 0,
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1)
            }
        
        return JsonResponse({
            "predictions": new_data[['Prediction', 'Actual', 'Correct', 'Fraud_Probability']].fillna("Unknown").to_dict(orient='records'),
            "message": "Fraud detection completed successfully.",
            "metrics": metrics
        })
    
    except Exception as e:
        print(f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)