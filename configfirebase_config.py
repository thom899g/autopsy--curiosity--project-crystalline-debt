"""
Firebase configuration and credential management with fallback strategies
"""
import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
import logging
from dataclasses import dataclass

@dataclass
class FirebaseConfig:
    """Firebase configuration with validation"""
    project_id: str
    database_url: Optional[str] = None
    storage_bucket: Optional[str] = None
    service_account_path: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'FirebaseConfig':
        """Load configuration from environment variables"""
        project_id = os.getenv('FIREBASE_PROJECT_ID', 'crystalline-debt-autopsy')
        
        # Check for service account JSON in multiple locations
        service_account_path = None
        possible_paths = [
            '/secure/firebase-key.json',
            'config/firebase-key.json',
            os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
            Path.home() / '.config/firebase-key.json'
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                service_account_path = path
                break
        
        return cls(
            project_id=project_id,
            database_url=os.getenv('FIREBASE_DATABASE_URL'),
            storage_bucket=os.getenv('FIREBASE_STORAGE_BUCKET'),
            service_account_path=service_account_path
        )
    
    def validate(self) -> bool:
        """Validate configuration has minimum required fields"""
        if not self.project_id:
            logging.error("Firebase project_id is required")
            return False
        
        # Service account not strictly required if using ADC
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for firebase-admin initialization"""
        config = {'projectId': self.project_id}
        
        if self.database_url:
            config['databaseURL'] = self.database_url
        if self.storage_bucket:
            config['storageBucket'] = self.storage_bucket
        
        return config

def initialize_firebase_with_fallback() -> bool:
    """
    Initialize Firebase with multiple fallback strategies
    
    Returns:
        bool: True if Firebase initialized successfully
    """
    config = FirebaseConfig.from_env()
    
    if not config.validate():
        logging.warning("Firebase configuration invalid, falling back to local mode")
        return False
    
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        # Check if already initialized
        if firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
            logging.info("Firebase already initialized")
            return True
        
        # Try service account file first
        if config.service_account_path:
            cred = credentials.Certificate(config.service_account_path)
            firebase_admin.initialize_app(cred, config.to_dict())
            logging.info(f"Firebase initialized with service account: {config.service_account_path}")
            return True
        
        # Try Application Default Credentials (ADC)
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, config.to_dict())
        logging.info("Firebase initialized with Application Default Credentials")
        return True
        
    except Exception as e:
        logging.error(f"Firebase initialization failed: {e}")