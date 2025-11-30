'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _callOrUse = require('./utils/callOrUse');

var _callOrUse2 = _interopRequireDefault(_callOrUse);

var _updateProps = require('./utils/updateProps');

var _updateProps2 = _interopRequireDefault(_updateProps);

var _mapValues = require('./utils/mapValues');

var _mapValues2 = _interopRequireDefault(_mapValues);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Passes state object properties and immutable updater functions in a form of
 * `(...payload: any[]) => Object` to the base component.
 *
 * Every state updater function accepts state, props and payload and must return
 * a new state or undefined. The new state is shallowly merged with the previous
 * state.
 *
 * @static
 * @category Higher-order-components
 * @param {Object|Function} initialState
 * @param {Object} stateUpdaters
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * const Counter = withStateHandlers(
 *   ({ initialCounter = 0 }) => ({
 *     counter: initialCounter,
 *   }),
 *   {
 *     incrementOn: ({ counter }) => (value) => ({
 *       counter: counter + value,
 *     }),
 *     decrementOn: ({ counter }) => (value) => ({
 *       counter: counter - value,
 *     }),
 *     resetCounter: (_, { initialCounter = 0 }) => () => ({
 *       counter: initialCounter,
 *     }),
 *   }
 * )(
 *   ({ counter, incrementOn, decrementOn, resetCounter }) =>
 *     <div>
 *       <Button onClick={() => incrementOn(2)}>Inc</Button>
 *       <Button onClick={() => decrementOn(3)}>Dec</Button>
 *       <Button onClick={resetCounter}>Reset</Button>
 *     </div>
 * )
 */
var withStateHandlers = function withStateHandlers(initialState, stateUpdaters) {
  return (0, _updateProps2.default)(function (next) {
    var props = void 0;
    var state = void 0;

    var handlers = (0, _mapValues2.default)(stateUpdaters, function (handler) {
      return function () {
        var updatedState = handler(state, props).apply(undefined, arguments);
        if (!updatedState) return;

        state = _extends({}, state, updatedState);
        next(_extends({}, props, state, handlers));
      };
    });

    return function (nextProps) {
      if (!props) state = (0, _callOrUse2.default)(initialState, nextProps);
      props = nextProps;
      next(_extends({}, props, state, handlers));
    };
  });
};

exports.default = (0, _createHelper2.default)(withStateHandlers, 'withStateHandlers');