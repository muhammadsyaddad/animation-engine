'use strict';

exports.__esModule = true;

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

/* eslint-disable class-methods-use-this */
var NonTrackingDummyWeakMap = function () {
  function NonTrackingDummyWeakMap() {
    _classCallCheck(this, NonTrackingDummyWeakMap);
  }

  NonTrackingDummyWeakMap.prototype.get = function get() {};

  NonTrackingDummyWeakMap.prototype.set = function set() {
    return this;
  };

  NonTrackingDummyWeakMap.prototype.has = function has() {
    return false;
  };

  return NonTrackingDummyWeakMap;
}();

exports.default = typeof WeakMap === 'undefined' ? NonTrackingDummyWeakMap : WeakMap;