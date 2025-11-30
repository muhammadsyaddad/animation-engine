'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; }; /* eslint-disable no-use-before-define */


var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _callOrUse = require('./utils/callOrUse');

var _callOrUse2 = _interopRequireDefault(_callOrUse);

var _updateProps = require('./utils/updateProps');

var _updateProps2 = _interopRequireDefault(_updateProps);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Passes two additional props to the base component: a state value, and a function
 * to update that state value. The state updater has the following signature:
 *
 * ```js
 * stateUpdater<T>((prevValue: T) => T): void
 * stateUpdater(newValue: any): void
 * ```
 *
 * The first form accepts a function which maps the previous state value to a new
 * state value. You'll likely want to use this state updater along with `withHandlers()`
 * or `withProps()` to create specific updater functions. For example, to create an
 * HoC that adds basic counting functionality to a component:
 *
 * ```js
 * const addCounting = compose(
 *   withState('counter', 'setCounter', 0),
 *   withProps(({ setCounter }) => ({
 *     increment: () => setCounter(n => n + 1),
 *     decrement: () => setCounter(n => n - 1),
 *     reset: () => setCounter(0)
 *   }))
 * )
 * ```
 *
 * The second form accepts a single value, which is used as the new state.
 *
 * An initial state value is required. It can be either the state value itself,
 * or a function that returns an initial state given the initial props.
 *
 * @static
 * @category Higher-order-components
 * @param {String} stateName
 * @param {String} stateUpdaterName
 * @param {*|Function} initialState
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 */
var withState = function withState(stateName, stateUpdaterName, initialState) {
  return (0, _updateProps2.default)(function (next) {
    var props = void 0;
    var state = void 0;

    var stateUpdater = function stateUpdater(nextState, callback) {
      var _extends2;

      if (process.env.NODE_ENV !== 'production' && callback) {
        /* eslint-disable no-console */
        console.error("Warning: withState(): the state updater's callback is not supported." + 'See https://github.com/neoziro/recompact/issues/59 for more details.');
        /* eslint-enable no-console */
      }
      state = (0, _callOrUse2.default)(nextState, state);
      next(_extends({}, props, (_extends2 = {}, _extends2[stateName] = state, _extends2[stateUpdaterName] = stateUpdater, _extends2)));
    };

    return function (nextProps) {
      var _extends3;

      if (!props) state = (0, _callOrUse2.default)(initialState, nextProps);
      props = nextProps;
      next(_extends({}, props, (_extends3 = {}, _extends3[stateName] = state, _extends3[stateUpdaterName] = stateUpdater, _extends3)));
    };
  });
};

exports.default = (0, _createHelper2.default)(withState, 'withState');