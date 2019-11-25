from logging import getLogger

import etcd3

from src import const

logger = getLogger(__name__)


class EtcdLockDoesNotAcquired(Exception):
    pass


class EtcdLock:
    _etcd_client = None

    def __init__(self, name, timeout=const.DEFAULT_LOCK_TIMEOUT_SEC):
        if EtcdLock._etcd_client is None:
            EtcdLock._etcd_client = etcd3.client(host=const.ETCD_HOST, port=const.ETCD_PORT)
            logger.debug('etcd_client created')
        self.name = name
        self.timeout = timeout
        self.lock = None

    def __enter__(self):
#        self.lock = EtcdLock._etcd_client.lock(self.name, ttl=const.ETCD_LOCK_TTL_SEC)
#        if not self.lock.acquire(timeout=self.timeout):
#            msg = f'can not acquire etcd.lock for {self.name}'
#            logger.warn(msg)
#            raise EtcdLockDoesNotAcquired(msg)
#        logger.debug(f'acquire etcd.lock for {self.name}')
        return self

    def __exit__(self, ex_type, ex_value, trace):
        pass
#        if self.lock is not None:
#            self.lock.release()
#            logger.debug(f'release etcd.lock for {self.name}')
