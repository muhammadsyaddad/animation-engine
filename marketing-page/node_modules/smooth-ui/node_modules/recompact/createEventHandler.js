'use strict';

exports.__esModule = true;
exports.createEventHandlerWithConfig = undefined;

var _symbolObservable = require('symbol-observable');

var _symbolObservable2 = _interopRequireDefault(_symbolObservable);

var _createChangeEmitter = require('./utils/createChangeEmitter');

var _createChangeEmitter2 = _interopRequireDefault(_createChangeEmitter);

var _setObservableConfig = require('./setObservableConfig');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var createEventHandlerWithConfig = exports.createEventHandlerWithConfig = function createEventHandlerWithConfig(config) {
  return function () {
    var _config$fromESObserva;

    var emitter = (0, _createChangeEmitter2.default)();
    var stream = config.fromESObservable((_config$fromESObserva = {
      subscribe: function subscribe(observer) {
        var unsubscribe = emitter.listen(function (value) {
          return observer.next(value);
        });
        return { unsubscribe: unsubscribe };
      }
    }, _config$fromESObserva[_symbolObservable2.default] = function () {
      return this;
    }, _config$fromESObserva));
    return {
      handler: emitter.emit,
      stream: stream
    };
  };
};

/**
 * Returns an object with properties handler and stream. stream is an observable
 * sequence, and handler is a function that pushes new values onto the sequence.
 * Useful for creating event handlers like onClick.
 *
 * @static
 * @category Utilities
 * @returns {Object} eventHandler
 * @returns {Function} eventHandler.handler
 * @returns {Observable} eventHandler.stream
 * @example
 *
 * const {handler, stream} = createEventHandler();
 */
var createEventHandler = createEventHandlerWithConfig(_setObservableConfig.config);

exports.default = createEventHandler;