"""
Repositorio: encapsula todas las consultas SQL sobre lecturas,
alertas, outliers, estado de conexión y consultas de menú.
"""
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.lectura import Lectura
from app.models.alerta import Alerta
from app.models.outlier_detectado import OutlierDetectado
from app.models.estado_conexion import EstadoConexion
from app.models.consulta_menu import ConsultaMenu
from app.models.umbral_alerta import UmbralAlerta


class LecturaRepository:
    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------------
    #  Lecturas
    # ----------------------------------------------------------------

    def crear(self, id_sensor: int, valor: float, tiempo: datetime | None = None) -> Lectura:
        lectura = Lectura(
            id_sensor=id_sensor,
            valor=valor,
            tiempo=tiempo or datetime.utcnow(),
            reenviada=False,
        )
        self.db.add(lectura)
        self.db.commit()
        self.db.refresh(lectura)
        return lectura

    def listar(
        self,
        id_sensor: int | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int = 500,
    ) -> list[Lectura]:
        query = self.db.query(Lectura)
        if id_sensor is not None:
            query = query.filter(Lectura.id_sensor == id_sensor)
        if desde is not None:
            query = query.filter(Lectura.tiempo >= desde)
        if hasta is not None:
            query = query.filter(Lectura.tiempo <= hasta)
        return query.order_by(Lectura.tiempo.desc()).limit(limite).all()

    # ----------------------------------------------------------------
    #  Alertas
    # ----------------------------------------------------------------

    def obtener_umbral(self, id_tipo_sensor: int) -> UmbralAlerta | None:
        """Devuelve el primer umbral activo para ese tipo de sensor."""
        return (
            self.db.query(UmbralAlerta)
            .filter(
                UmbralAlerta.id_tipo_sensor == id_tipo_sensor,
                UmbralAlerta.activo == True,
            )
            .first()
        )

    def registrar_alerta(
        self,
        id_sensor: int,
        id_umbral: int,
        tiempo_lectura: datetime,
        valor: float,
    ) -> Alerta:
        alerta = Alerta(
            id_sensor=id_sensor,
            id_umbral=id_umbral,
            tiempo_lectura=tiempo_lectura,
            valor=valor,
            estado="ACTIVA",
        )
        self.db.add(alerta)
        self.db.commit()
        return alerta

    def listar_alertas(self, limite: int = 100) -> list[Alerta]:
        return (
            self.db.query(Alerta)
            .order_by(Alerta.creada_en.desc())
            .limit(limite)
            .all()
        )

    # ----------------------------------------------------------------
    #  Outliers
    # ----------------------------------------------------------------

    def registrar_outlier(
        self,
        id_sensor: int,
        tiempo_lectura: datetime,
        valor: float,
        z_score: float | None = None,
        metodo: str = "zscore",
    ) -> OutlierDetectado:
        outlier = OutlierDetectado(
            id_sensor=id_sensor,
            tiempo_lectura=tiempo_lectura,
            valor=valor,
            z_score=z_score,
            metodo=metodo,
        )
        self.db.add(outlier)
        self.db.commit()
        return outlier

    def listar_outliers(self, id_sensor: int | None = None, limite: int = 100) -> list[OutlierDetectado]:
        query = self.db.query(OutlierDetectado)
        if id_sensor is not None:
            query = query.filter(OutlierDetectado.id_sensor == id_sensor)
        return query.order_by(OutlierDetectado.detectado_en.desc()).limit(limite).all()

    # ----------------------------------------------------------------
    #  Estado de conexión
    # ----------------------------------------------------------------

    def registrar_estado_conexion(
        self,
        id_dispositivo: int,
        conectado: bool,
        rssi_dbm: int | None,
        reintentos: int,
        lecturas_en_buffer: int,
    ) -> EstadoConexion:
        evento = EstadoConexion(
            id_dispositivo=id_dispositivo,
            conectado=conectado,
            rssi_dbm=rssi_dbm,
            reintentos=reintentos,
            lecturas_en_buffer=lecturas_en_buffer,
        )
        self.db.add(evento)
        self.db.commit()
        self.db.refresh(evento)
        return evento

    # ----------------------------------------------------------------
    #  Consultas menú
    # ----------------------------------------------------------------

    def registrar_consulta_menu(self, id_dispositivo: int, tecla: str) -> ConsultaMenu:
        consulta = ConsultaMenu(id_dispositivo=id_dispositivo, tecla=tecla)
        self.db.add(consulta)
        self.db.commit()
        self.db.refresh(consulta)
        return consulta
