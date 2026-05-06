import numpy as np

from pyplasmod.exceptions import PlasmodException


def float_vector_validator(x: object, dim: int):
    if isinstance(x, list):  # accepts list of float
        if len(x) != dim:
            raise PlasmodException(message="array's length must be equal to vector dimension")

        for k in x:
            if not isinstance(k, float):
                raise PlasmodException(message="array's element must be float value")
        return x

    if isinstance(x, np.ndarray):  # accepts numpy array of float
        if (not issubclass(x.dtype.type, np.float32)) and (
            not issubclass(x.dtype.type, np.float64)
        ):
            msg = (
                'numpy.ndarray\'s dtype must be "float32" or "float64" for FLOAT_VECTOR type field'
            )
            raise PlasmodException(message=msg)

        if len(x.shape) != 1:
            raise PlasmodException(message="numpy.ndarray's shape must not be one dimension")

        if x.shape[0] != dim:
            raise PlasmodException(
                message="numpy.ndarray's length must be equal to vector dimension"
            )

        return x.tolist()

    raise PlasmodException(
        message="only accept numpy.ndarray or list[float] for FLOAT_VECTOR type field"
    )


def binary_vector_validator(x: object, dim: int):
    if isinstance(x, list):  # accepts list such as [1, 0, 1, 1, 0, 0, 1, 0]
        if len(x) != dim:
            raise PlasmodException(message="length of the list must be equal to vector dimension")
        return np.packbits(x, axis=-1).tolist()

    if isinstance(x, bytes):  # accepts bytes such as b'\x00\x01\x02\x03'
        x = np.frombuffer(x, dtype=np.uint8).tolist()
        if len(x) * 8 != dim:
            raise PlasmodException(
                message="length of the bytes must be equal to 8x of vector dimension"
            )
        return x

    if isinstance(x, np.ndarray):  # accepts numpy array of uint8
        if not issubclass(x.dtype.type, np.uint8):
            msg = 'numpy.ndarray\'s dtype must be "uint8" for BINARY_VECTOR type field'
            raise PlasmodException(message=msg)

        if len(x.shape) != 1:
            raise PlasmodException(message="numpy.ndarray's shape must be one dimension")

        if x.shape[0] * 8 != dim:
            raise PlasmodException(
                message="numpy.ndarray's length must be equal to 8x of vector dimension"
            )

        return x.tolist()

    raise PlasmodException(
        message="only accept numpy.ndarray, list, bytes for BINARY_VECTOR type field"
    )


def float16_vector_validator(x: object, dim: int, is_bfloat: bool):
    if isinstance(x, list):  # accepts list of float
        if len(x) != dim:
            raise PlasmodException(message="array's length must be equal to vector dimension")

        for k in x:
            if not isinstance(k, float):
                raise PlasmodException(message="array's element must be float value")

        arr = (
            np.array(x, dtype=np.dtype("bfloat16")) if is_bfloat else np.array(x, dtype=np.float16)
        )
        return arr.tobytes()

    if isinstance(x, np.ndarray):  # accepts numpy array
        if is_bfloat and x.dtype != "bfloat16":
            msg = 'numpy.ndarray\'s dtype must be "bfloat16" for BFLOAT16_VECTOR type field'
            raise PlasmodException(message=msg)
        if (not is_bfloat) and (not issubclass(x.dtype.type, np.float16)):
            msg = 'numpy.ndarray\'s dtype must be "float16" for FLOAT16_VECTOR type field'
            raise PlasmodException(message=msg)

        if len(x.shape) != 1:
            raise PlasmodException(message="numpy.ndarray's shape must not be one dimension")

        if x.shape[0] != dim:
            raise PlasmodException(
                message="numpy.ndarray's length must be equal to vector dimension"
            )

        return x.tobytes()

    raise PlasmodException(
        message="only accept numpy.ndarray or list[float] for FLOAT16_VECTOR/BFLOAT16_VECTOR type field"
    )


def int8_vector_validator(x: object, dim: int):
    if isinstance(x, list):  # accepts list of int
        if len(x) != dim:
            raise PlasmodException(message="array's length must be equal to vector dimension")

        for k in x:
            if not isinstance(k, int):
                raise PlasmodException(message="array's element must be int value")
        return x

    if isinstance(x, np.ndarray):  # accepts numpy array of int
        if not issubclass(x.dtype.type, np.int8):
            msg = 'numpy.ndarray\'s dtype must be "int8" for INT8_VECTOR type field'
            raise PlasmodException(message=msg)

        if len(x.shape) != 1:
            raise PlasmodException(message="numpy.ndarray's shape must not be one dimension")

        if x.shape[0] != dim:
            raise PlasmodException(
                message="numpy.ndarray's length must be equal to vector dimension"
            )

        return x.tolist()

    raise PlasmodException(
        message="only accept numpy.ndarray or list[int8] for INT8_VECTOR type field"
    )


def sparse_vector_validator(x: object):
    if not isinstance(x, dict):
        raise PlasmodException(message="only accept dict for SPARSE_FLOAT_VECTOR type field")

    def check_pair(k: object, v: object):
        if not isinstance(k, int):
            raise PlasmodException(message="sparse vector's index must be integer value")
        if not isinstance(v, float):
            raise PlasmodException(message="sparse vector's value must be float value")

    # only accepts dict like {2: 13.23, 45: 0.54} or {"indices": [1, 2], "values": [0.1, 0.2]}
    if "indices" in x and "values" in x:
        indices = x["indices"]
        values = x["values"]
        if not isinstance(indices, list):
            raise PlasmodException(message="indices of sparse vector must be a list of int")
        if not isinstance(values, list):
            raise PlasmodException(message="values of sparse vector must be a list of int")
        if len(indices) != len(values):
            raise PlasmodException(
                message="length of indices and values of sparse vector must be equal"
            )
        if len(indices) == 0:
            raise PlasmodException(message="empty sparse vector is not allowed")
        for i in range(len(indices)):
            check_pair(indices[i], values[i])
    else:
        if len(x) == 0:
            raise PlasmodException(message="empty sparse vector is not allowed")
        for key, value in x.items():
            check_pair(key, value)

    return x


def struct_validator(x: object, max_cap: int):
    if not isinstance(x, list):
        raise PlasmodException(message="only accept list of dict for STRUCT type field")
    if len(x) > max_cap:
        raise PlasmodException(message="array's length must be less or equal than max_capacity")
    for k in x:
        if not isinstance(k, dict):
            raise PlasmodException(message="only accept list of dict for STRUCT type field")
    return True
