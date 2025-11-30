'use strict';

exports.__esModule = true;

var _createObservable = require('./createObservable');

var _createObservable2 = _interopRequireDefault(_createObservable);

var _createHOCFromMapper = require('./createHOCFromMapper');

var _createHOCFromMapper2 = _interopRequireDefault(_createHOCFromMapper);

var _setObservableConfig = require('../setObservableConfig');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var updateProps = function updateProps(subscriber) {
  return (0, _createHOCFromMapper2.default)(function (props$, obs) {
    return [(0, _createObservable2.default)(function (observer) {
      return _setObservableConfig.config.toESObservable(props$).subscribe({
        next: subscriber(function (value) {
          observer.next(value);
        }),
        error: typeof observer.error === 'function' ? function (error) {
          observer.error(error);
        } : undefined,
        complete: typeof observer.complete === 'function' ? function (value) {
          observer.complete(value);
        } : undefined
      });
    }), obs];
  });
};

exports.default = updateProps;