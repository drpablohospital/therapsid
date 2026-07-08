"""
Therapsid - Federated Learning con Flower
Entrenamiento colaborativo de modelos ML sin compartir datos
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional
import numpy as np


class MortalityPredictor(nn.Module):
    """
    Modelo de predicción de mortalidad en UCI.
    Input: 20 features (scores, labs, signos vitales)
    Output: Probabilidad de mortalidad (0-1)
    """
    
    def __init__(self, input_dim: int = 20, hidden_dim: int = 64):
        super().__init__()
        self.layer1 = nn.Linear(input_dim, hidden_dim)
        self.dropout1 = nn.Dropout(0.3)
        self.layer2 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.dropout2 = nn.Dropout(0.2)
        self.layer3 = nn.Linear(hidden_dim // 2, 1)
        
    def forward(self, x):
        x = F.relu(self.layer1(x))
        x = self.dropout1(x)
        x = F.relu(self.layer2(x))
        x = self.dropout2(x)
        x = torch.sigmoid(self.layer3(x))
        return x


class LocalDataLoader:
    """
    Carga datos locales para entrenamiento federado.
    Extrae features de la base de datos SQLite local.
    """
    
    # Features que usa el modelo (20 variables)
    FEATURE_COLUMNS = [
        # Scores
        'sofa_total', 'saps3', 'apache', 'charlson',
        # Signos vitales
        'fc', 'tas', 'tad', 'temperatura', 'fr',
        # Labs
        'lactato', 'creatinina', 'urea', 'leucocitos',
        'plaquetas', 'hemoglobina', 'ph', 'pao2',
        # Otros
        'edad', 'dias_ventilacion', 'num_dispositivos',
    ]
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def load_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Carga datos de entrenamiento desde SQLite local.
        
        Returns:
            X: Array de features (n_samples, 20)
            y: Array de labels (n_samples, 1) - 1=mortalidad
        """
        import sqlite3
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Intentar cargar de tabla evoluciones
            cursor.execute("""
                SELECT 
                    sofa_total, saps3, apache, charlson_index,
                    fc, tas, tad, temperatura, fr,
                    lactato, creatinina, urea, leucocitos,
                    plaquetas, hemoglobina, ph, pao2,
                    edad, dias_ventilacion, num_dispositivos,
                    egreso
                FROM evolutions e
                JOIN patients p ON e.patient_id = p.id
                WHERE egreso IS NOT NULL
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                # No hay datos suficientes
                return np.array([]), np.array([])
            
            # Convertir a arrays
            data = np.array(rows)
            X = data[:, :-1]  # Todas las features
            y = (data[:, -1] == 'death').astype(np.float32).reshape(-1, 1)
            
            # Normalizar (z-score)
            X = self._normalize(X)
            
            return X, y
            
        except Exception as e:
            print(f"⚠️  [Therapsid] Error cargando datos: {e}")
            return np.array([]), np.array([])
    
    def _normalize(self, X: np.ndarray) -> np.ndarray:
        """Normaliza features con z-score"""
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)
        stds[stds == 0] = 1  # Evitar división por cero
        return (X - means) / stds


class FlowerClient:
    """
    Cliente Flower para entrenamiento federado.
    Corre localmente en cada nodo Therapsid.
    """
    
    def __init__(self, model: MortalityPredictor, data_loader: LocalDataLoader):
        self.model = model
        self.data_loader = data_loader
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
    
    def get_parameters(self) -> List[np.ndarray]:
        """Retorna los parámetros del modelo como arrays NumPy"""
        return [param.data.cpu().numpy() for param in self.model.parameters()]
    
    def set_parameters(self, parameters: List[np.ndarray]):
        """Actualiza los parámetros del modelo desde arrays NumPy"""
        for param, new_param in zip(self.model.parameters(), parameters):
            param.data = torch.tensor(new_param).to(self.device)
    
    def fit(self, parameters: List[np.ndarray], config: Dict) -> Tuple[List[np.ndarray], int, Dict]:
        """
        Entrena el modelo localmente con los datos del hospital.
        
        Args:
            parameters: Parámetros del modelo global
            config: Configuración del servidor (epochs, lr, etc.)
        
        Returns:
            (parámetros actualizados, num_samples, metrics)
        """
        # Actualizar parámetros del modelo global
        self.set_parameters(parameters)
        
        # Cargar datos locales
        X, y = self.data_loader.load_training_data()
        
        if len(X) == 0:
            # No hay datos locales, devolver parámetros sin cambios
            return self.get_parameters(), 0, {"loss": 0.0}
        
        # Convertir a tensores
        X_tensor = torch.tensor(X, dtype=torch.float32).to(self.device)
        y_tensor = torch.tensor(y, dtype=torch.float32).to(self.device)
        
        # Entrenamiento local
        epochs = config.get("epochs", 5)
        lr = config.get("learning_rate", 0.01)
        batch_size = config.get("batch_size", min(32, len(X)))
        
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = nn.BCELoss()
        
        self.model.train()
        for epoch in range(epochs):
            # Mini-batch training
            indices = torch.randperm(len(X_tensor))
            for i in range(0, len(X_tensor), batch_size):
                batch_idx = indices[i:i+batch_size]
                batch_X = X_tensor[batch_idx]
                batch_y = y_tensor[batch_idx]
                
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
        
        # Evaluar
        self.model.eval()
        with torch.no_grad():
            predictions = self.model(X_tensor)
            loss = criterion(predictions, y_tensor).item()
        
        # Retornar parámetros actualizados + métricas
        return self.get_parameters(), len(X), {"loss": loss}
    
    def evaluate(self, parameters: List[np.ndarray], config: Dict) -> Tuple[float, int, Dict]:
        """
        Evalúa el modelo con datos locales.
        
        Returns:
            (loss, num_samples, metrics)
        """
        self.set_parameters(parameters)
        
        X, y = self.data_loader.load_training_data()
        
        if len(X) == 0:
            return 0.0, 0, {"accuracy": 0.0}
        
        X_tensor = torch.tensor(X, dtype=torch.float32).to(self.device)
        y_tensor = torch.tensor(y, dtype=torch.float32).to(self.device)
        
        self.model.eval()
        criterion = nn.BCELoss()
        
        with torch.no_grad():
            predictions = self.model(X_tensor)
            loss = criterion(predictions, y_tensor).item()
            
            # Calcular accuracy
            predicted_labels = (predictions > 0.5).float()
            accuracy = (predicted_labels == y_tensor).float().mean().item()
        
        return loss, len(X), {"accuracy": accuracy}


def create_flower_client(db_path: str) -> FlowerClient:
    """Factory para crear un cliente Flower"""
    model = MortalityPredictor(input_dim=20, hidden_dim=64)
    data_loader = LocalDataLoader(db_path)
    return FlowerClient(model, data_loader)


# Configuración por defecto del servidor Flower
DEFAULT_SERVER_CONFIG = {
    "num_rounds": 10,           # Rondas de federación
    "fraction_fit": 0.5,        # 50% de nodos participan cada ronda
    "fraction_evaluate": 0.3,   # 30% de nodos evalúan
    "min_fit_clients": 2,       # Mínimo 2 nodos para entrenar
    "min_evaluate_clients": 1,  # Mínimo 1 nodo para evaluar
    "min_available_clients": 2, # Mínimo 2 nodos disponibles
}
