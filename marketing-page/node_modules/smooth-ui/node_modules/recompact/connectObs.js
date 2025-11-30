'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _typeof = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function (obj) { return typeof obj; } : function (obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; };

var _createObservable = require('./utils/createObservable');

var _createObservable2 = _interopRequireDefault(_createObservable);

var _asyncThrow = require('./utils/asyncThrow');

var _asyncThrow2 = _interopRequireDefault(_asyncThrow);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _withObs = require('./withObs');

var _withObs2 = _interopRequireDefault(_withObs);

var _setObservableConfig = require('./setObservableConfig');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var checkObsMap = function checkObsMap(obsMap) {
  if (process.env.NODE_ENV !== 'production') {
    if ((typeof obsMap === 'undefined' ? 'undefined' : _typeof(obsMap)) !== 'object') {
      throw new Error('connectObs(): The observable mapper must return a plain object, got ' + ('\'' + obsMap + '\' instead'));
    }
  }
};

var checkObserver = function checkObserver(observer, name) {
  if (process.env.NODE_ENV !== 'production') {
    if (!observer || !observer.next) {
      throw new Error('connectObs(): Expected \'' + name + '\' to be an Observer, got ' + ('\'' + observer + '\' instead.'));
    }
  }
};

var checkObservable = function checkObservable(observable, name) {
  if (process.env.NODE_ENV !== 'production') {
    if (!observable || !observable.subscribe) {
      throw new Error('connectObs(): Expected \'' + name + '\' to be an Observable, got ' + ('\'' + observable + '\' instead.'));
    }
  }
};

/**
 * Connect observables to props using a map.
 *
 * - The function take one argument, an object containing context observables
 * and a special observable `props$` that emits owner props.
 * - The property is updated at each emission of a new value by the associated
 * Observable.
 * - Properties matching `/^on[A-Z]/` are mapped to the `next` method of
 * the associated Observer.
 *
 * @static
 * @category Higher-order-components
 * @param {Function} obsMapper The function that takes observables and returns map.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * connectObs(({change$, value$}) => ({
 *   onChange: change$,
 *   value: value$,
 * }))('input');
 */
var connectObs = function connectObs(obsMapper) {
  return (0, _withObs2.default)(function (observables) {
    var nextProps$ = (0, _createObservable2.default)(function (observer) {
      var obsMap = obsMapper(observables);
      var obsProps = {};
      var obsSubscriptions = [];
      var props = void 0;

      checkObsMap(obsMap);

      var update = function update() {
        if (props) {
          observer.next(_extends({}, props, obsProps));
        }
      };

      Object.keys(obsMap).forEach(function (key) {
        if (key.match(/^on[A-Z]/)) {
          var observable = obsMap[key];
          checkObserver(observable, key);
          obsProps[key] = observable.next.bind(observable);
        } else {
          var _observable = _setObservableConfig.config.toESObservable(obsMap[key]);
          checkObservable(_observable, key);
          obsProps[key] = undefined;
          var subscription = _observable.subscribe({
            next: function next(value) {
              obsProps[key] = value;
              update();
            },

            error: _asyncThrow2.default
          });

          obsSubscriptions.push(subscription);
        }
      });

      var propsSubscription = _setObservableConfig.config.toESObservable(observables.props$).subscribe({
        next: function next(nextProps) {
          props = nextProps;
          update();
        },

        error: _asyncThrow2.default
      });

      return function () {
        propsSubscription.unsubscribe();
        obsSubscriptions.forEach(function (subscription) {
          subscription.unsubscribe();
        });
      };
    });

    return { props$: nextProps$ };
  });
};

exports.default = (0, _createHelper2.default)(connectObs, 'connectObs');