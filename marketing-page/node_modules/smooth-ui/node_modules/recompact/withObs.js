'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _callOrUse = require('./utils/callOrUse');

var _callOrUse2 = _interopRequireDefault(_callOrUse);

var _createHOCFromMapper = require('./utils/createHOCFromMapper');

var _createHOCFromMapper2 = _interopRequireDefault(_createHOCFromMapper);

var _shareObservable = require('./utils/shareObservable');

var _shareObservable2 = _interopRequireDefault(_shareObservable);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Takes observables from the context and special observable `props$` and map them
 * to a new set of observables.
 *
 * @static
 * @category Higher-order-components
 * @param {Function} obsMapper The function that take previous observables and returns new ones.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * const withFullName$ = mapObs(({firstName$, props$}) => ({
 *  fullName$: Observable.combineLatest(
 *    firstName$,
 *    props$.pluck('lastName'),
 *    (firstName, lastName) => `${firstName} ${lastName}`
 *   )
 * }))
 */
var withObs = function withObs(obsMapper) {
  return (0, _createHOCFromMapper2.default)(function (props$, obs) {
    var sharedProps$ = (0, _shareObservable2.default)(props$);
    var nextObs = (0, _callOrUse2.default)(obsMapper, _extends({}, obs, { props$: sharedProps$ }));
    var _nextObs$props$ = nextObs.props$,
        nextProps$ = _nextObs$props$ === undefined ? props$ : _nextObs$props$;

    delete nextObs.props$;
    return [nextProps$, _extends({}, obs, nextObs)];
  });
};

exports.default = (0, _createHelper2.default)(withObs, 'withObs');