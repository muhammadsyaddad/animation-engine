'use strict';

exports.__esModule = true;

var _createObservable = require('./createObservable');

var _createObservable2 = _interopRequireDefault(_createObservable);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var shareObservable = function shareObservable(observable) {
  var observers = [];
  var emitted = false;
  var lastValue = void 0;
  var subscription = null;

  return (0, _createObservable2.default)(function (observer) {
    if (!subscription) {
      subscription = observable.subscribe({
        next: function next(value) {
          emitted = true;
          lastValue = value;
          observers.forEach(function (o) {
            return o.next(value);
          });
        },
        complete: function complete(value) {
          return observers.forEach(function (o) {
            return o.complete(value);
          });
        },
        error: function error(_error) {
          return observers.forEach(function (o) {
            return o.error(_error);
          });
        }
      });
    }

    observers.push(observer);

    if (emitted) {
      observer.next(lastValue);
    }

    return {
      unsubscribe: function unsubscribe() {
        var index = observers.indexOf(observer);
        if (index === -1) return;
        observers.splice(index, 1);

        if (observers.length === 0) {
          subscription.unsubscribe();
          emitted = false;
          subscription = null;
        }
      }
    };
  });
}; /* eslint-disable import/prefer-default-export */
exports.default = shareObservable;