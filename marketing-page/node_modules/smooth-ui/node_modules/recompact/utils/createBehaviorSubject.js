'use strict';

exports.__esModule = true;

var _createChangeEmitter = require('./createChangeEmitter');

var _createChangeEmitter2 = _interopRequireDefault(_createChangeEmitter);

var _createObservable = require('./createObservable');

var _createObservable2 = _interopRequireDefault(_createObservable);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/* eslint-disable import/prefer-default-export */
var noop = function noop() {};

var createBehaviorSubject = function createBehaviorSubject(initial) {
  var last = initial;
  var emitter = (0, _createChangeEmitter2.default)();
  var complete = noop;
  var observable = (0, _createObservable2.default)(function (observer) {
    var unsubscribe = emitter.listen(function (value) {
      last = value;
      observer.next(value);
    });
    observer.next(last);
    complete = observer.complete ? observer.complete.bind(observer) : complete;
    return { unsubscribe: unsubscribe };
  });
  observable.next = emitter.emit;
  observable.complete = function () {
    complete();
  };
  return observable;
};

exports.default = createBehaviorSubject;