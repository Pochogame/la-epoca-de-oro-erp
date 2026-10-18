class ErrorDeNegocio(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


class AutenticacionError(ErrorDeNegocio):
    pass


class DatosInvalidosError(ErrorDeNegocio):
    pass


class StockInsuficienteError(ErrorDeNegocio):
    pass


class OperacionDuplicadaError(ErrorDeNegocio):
    pass
