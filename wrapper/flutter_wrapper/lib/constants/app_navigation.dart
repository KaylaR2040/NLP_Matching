import 'package:flutter/material.dart';

/// Shared [RouteObserver] used to detect route lifecycle events.
///
/// Register screens that need to react to being navigated back to
/// (e.g. to refresh stale data) using [RouteAware].
///
/// Add [routeObserver] to [MaterialApp.navigatorObservers] in main.dart.
final RouteObserver<ModalRoute<void>> routeObserver =
    RouteObserver<ModalRoute<void>>();
