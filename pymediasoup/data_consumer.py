import logging
from typing import Optional, Any
from pydantic import BaseModel
from pyee import AsyncIOEventEmitter
from aiortc import RTCDataChannel
from .emitter import EnhancedEventEmitter
from .sctp_parameters import SctpStreamParameters


class DataConsumerOptions(BaseModel):
    id: Optional[str]
    dataProducerId: Optional[str]
    sctpStreamParameters: SctpStreamParameters
    label: Optional[str]
    protocol: Optional[str]
    appData: Optional[dict] = None

class DataConsumer(EnhancedEventEmitter):
    # Closed flag.
    _closed: bool = False
    # Observer instance.
    _observer: AsyncIOEventEmitter = AsyncIOEventEmitter()

    def __init__(
        self,
        id: str,
        dataProducerId: str,
        dataChannel: RTCDataChannel,
        sctpStreamParameters: SctpStreamParameters,
        appData: Optional[dict] = None,
        loop=None
    ):
        super(DataConsumer, self).__init__(loop=loop)

        self._id = id
        self._dataProducerId = dataProducerId
        self._dataChannel = dataChannel
        self._sctpStreamParameters = sctpStreamParameters
        self._appData = appData

        self._handleDataChannel()
    
    # DataConsumer id.
    @property
    def id(self) -> str:
        return self._id
    
    # Associated DataProducer id.
    @property
    def dataProducerId(self) -> str:
        return self._dataProducerId
    
    # Whether the DataConsumer is closed.
    @property
    def closed(self) -> bool:
        return self._closed
    
    # SCTP stream parameters.
    @property
    def sctpStreamParameters(self) -> SctpStreamParameters:
        return self._sctpStreamParameters
    
    # DataChannel readyState.
    @property
    def readyState(self) -> RTCDataChannelState:
        return self._dataChannel.readyState
    
    # DataChannel label.
    @property
    def label(self) -> str:
        return self._dataChannel.label
    
    # DataChannel protocol.
    @property
    def protocol(self) -> str:
        return self._dataChannel.protocol

    # DataChannel binaryType.
    @property
    def binaryType(self) -> str:
        return self._dataChannel.binaryType
    
    @binaryType.setter
    def binaryType(self, binaryType: str):
        self._dataChannel.binaryType = binaryType
    
    # App custom data.
    @property
    def appData(self) -> Any:
        return self._appData
    
    # Invalid setter.
    @appData.setter
    def appData(self, value):
        raise Exception('cannot override appData object')
    
    # Observer.
    @property
    def observer(self) -> AsyncIOEventEmitter:
        return self._observer
    
    # Closes the DataConsumer.
    def close(self):
        if self._closed:
            return
        
        logging.debug('DataConsumer close()')

        self._closed = True

        self._destroyTrack()

        self.emit('@close')

        # Emit observer event.
        self._observer.emit('close')
    
    # Transport was closed.
    def transportClosed(self):
        if self._closed:
            return

        logging.debug('DataConsumer transportClosed()')

        self._closed = True

        self._destroyTrack()

        self.emit('transportclose')

        self._observer.emit('close')
    
    def _handleDataChannel(self):
        @self._dataChannel.on('open')
        def on_open():
            if self._closed:
                return
            logging.debug('DataConsumer DataChannel "open" event')
            self.emit('open')

        # NOTE: aiortc.RTCDataChannel won't emit error event, here use pyee error event
        @self._dataChannel.on('error')
        def on_error(message):
            if self._closed:
                return

            logging.error(f'DataConsumer DataChannel "error" event: {message}')
            
            self.emit('error', message)

        @self._dataChannel.on('close')
        def on_close():
            if self._closed:
                return
            logging.warning('DataConsumer DataChannel "close" event')
            self._closed = True
            self.emit('@close')
            self._observer.emit('close')

        @self._dataChannel.on('message')
        def on_message(message):
            if self._closed:
                return
            self.emit('message', message)
