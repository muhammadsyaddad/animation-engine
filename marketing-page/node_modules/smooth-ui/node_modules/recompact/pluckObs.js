'use strict';

exports.__esModule = true;

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _connectObs = require('./connectObs');

var _connectObs2 = _interopRequireDefault(_connectObs);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Takes a list of observable names, find the corresponding observables
 * from the context and map them to the corresponding prop according the
 * convention i.e.: same name without a $ at the end.
 *
 * @static
 * @category Higher-order-components
 * @param {Function} observablesNames
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 */
var pluckObs = function pluckObs() {
  for (var _len = arguments.length, observableNames = Array(_len), _key = 0; _key < _len; _key++) {
    observableNames[_key] = arguments[_key];
  }

  return (0, _connectObs2.default)(function (observables) {
    return Object.assign.apply(Object, observableNames.map(function (observableName) {
      var _ref;

      return _ref = {}, _ref[observableName.replace(/\$$/, '')] = observables[observableName], _ref;
    }));
  });
};

exports.default = (0, _createHelper2.default)(pluckObs, 'pluckObs');