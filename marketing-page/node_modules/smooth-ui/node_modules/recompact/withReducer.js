'use strict';

exports.__esModule = true;
exports.INIT = undefined;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; }; /* eslint-disable no-use-before-define */


var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _createSymbol = require('./utils/createSymbol');

var _createSymbol2 = _interopRequireDefault(_createSymbol);

var _callOrUse = require('./utils/callOrUse');

var _callOrUse2 = _interopRequireDefault(_callOrUse);

var _updateProps = require('./utils/updateProps');

var _updateProps2 = _interopRequireDefault(_updateProps);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var INIT = exports.INIT = (0, _createSymbol2.default)('INIT');

/**
 * Similar to `withState()`, but state updates are applied using a reducer function.
 * A reducer is a function that receives a state and an action, and returns a new state.
 *
 * Passes two additional props to the base component: a state value, and a
 * dispatch method. The dispatch method sends an action to the reducer, and
 * the new state is applied.
 *
 * @static
 * @category Higher-order-components
 * @param {String} stateName
 * @param {String} dispatchName
 * @param {Function} reducer
 * @param {*} initialState
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * const counterReducer = (count, action) => {
 *   switch (action.type) {
 *   case INCREMENT:
 *     return count + 1
 *   case DECREMENT:
 *     return count - 1
 *   default:
 *     return count
 *   }
 * }
 *
 * const enhance = withReducer('counter', 'dispatch', counterReducer, 0)
 * const Counter = enhance(({ counter, dispatch }) =>
 *   <div>
 *     Count: {counter}
 *     <button onClick={() => dispatch({ type: INCREMENT })}>Increment</button>
 *     <button onClick={() => dispatch({ type: DECREMENT })}>Decrement</button>
 *   </div>
 * )
 */
var withReducer = function withReducer(stateName, dispatchName, reducer, initialState) {
  return (0, _updateProps2.default)(function (next) {
    var initialized = void 0;
    var state = void 0;
    var props = void 0;

    function dispatch(action) {
      updateState(reducer(state, action));
    }

    function updateState(nextState) {
      var _extends2;

      state = nextState;
      next(_extends({}, props, (_extends2 = {}, _extends2[stateName] = state, _extends2[dispatchName] = dispatch, _extends2)));
    }

    return function (nextProps) {
      props = nextProps;

      if (!initialized) {
        initialized = true;

        if (initialState !== undefined) {
          updateState((0, _callOrUse2.default)(initialState, props));
        } else {
          updateState(reducer(undefined, { type: INIT }));
        }
      } else {
        updateState(state);
      }
    };
  });
};

exports.default = (0, _createHelper2.default)(withReducer, 'withReducer');