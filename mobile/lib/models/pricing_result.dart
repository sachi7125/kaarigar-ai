// Mirrors backend/app/api/pricing.py's JSON shapes. (Day 4)

class AttributeSuggestion {
  final String transcript;
  final String category;
  final String material;
  final String materialSource;
  final String sizeClass;
  final double? sizeScore;
  final String sizeSource;
  final String finish;
  final String titleEn;
  final String titleHi;
  final String descriptionEn;
  final String descriptionHi;

  AttributeSuggestion({
    required this.transcript,
    required this.category,
    required this.material,
    required this.materialSource,
    required this.sizeClass,
    required this.sizeScore,
    required this.sizeSource,
    required this.finish,
    required this.titleEn,
    required this.titleHi,
    required this.descriptionEn,
    required this.descriptionHi,
  });

  factory AttributeSuggestion.fromJson(Map<String, dynamic> j) => AttributeSuggestion(
        transcript: j['transcript'] ?? '',
        category: j['category'] ?? '',
        material: j['material'] ?? '',
        materialSource: j['material_source'] ?? 'none',
        sizeClass: j['size_class'] ?? '',
        sizeScore: (j['size_score'] as num?)?.toDouble(),
        sizeSource: j['size_source'] ?? 'vision-suggested',
        finish: j['finish'] ?? 'unknown',
        titleEn: j['title_en'] ?? '',
        titleHi: j['title_hi'] ?? '',
        descriptionEn: j['description_en'] ?? '',
        descriptionHi: j['description_hi'] ?? '',
      );
}

class MaterialCost {
  final bool known;
  final double rateInrPerKg;
  final String rateDate;
  final String rateSource;
  final double weightKg;
  final double costInr;

  MaterialCost({
    required this.known,
    required this.rateInrPerKg,
    required this.rateDate,
    required this.rateSource,
    required this.weightKg,
    required this.costInr,
  });

  factory MaterialCost.fromJson(Map<String, dynamic> j) => MaterialCost(
        known: j['known'] ?? false,
        rateInrPerKg: (j['rate_inr_per_kg'] as num?)?.toDouble() ?? 0,
        rateDate: j['rate_date'] ?? '',
        rateSource: j['rate_source'] ?? '',
        weightKg: (j['weight_kg'] as num?)?.toDouble() ?? 0,
        costInr: (j['cost_inr'] as num?)?.toDouble() ?? 0,
      );
}

class FloorResult {
  final MaterialCost materialCost;
  final double labourHours;
  final double labourCostInr;
  final double floorInr;
  final bool known;

  FloorResult({
    required this.materialCost,
    required this.labourHours,
    required this.labourCostInr,
    required this.floorInr,
    required this.known,
  });

  factory FloorResult.fromJson(Map<String, dynamic> j) => FloorResult(
        materialCost: MaterialCost.fromJson(j['material_cost']),
        labourHours: (j['labour_hours'] as num?)?.toDouble() ?? 0,
        labourCostInr: (j['labour_cost_inr'] as num?)?.toDouble() ?? 0,
        floorInr: (j['floor_inr'] as num?)?.toDouble() ?? 0,
        known: j['known'] ?? false,
      );
}

class Comparable {
  final String category;
  final String material;
  final String size;
  final String region;
  final double priceInr;
  final String observedOrSynthesised;

  Comparable({
    required this.category,
    required this.material,
    required this.size,
    required this.region,
    required this.priceInr,
    required this.observedOrSynthesised,
  });

  factory Comparable.fromJson(Map<String, dynamic> j) => Comparable(
        category: j['category'] ?? '',
        material: j['material'] ?? '',
        size: j['size'] ?? '',
        region: j['region'] ?? '',
        priceInr: (j['price_inr'] as num?)?.toDouble() ?? 0,
        observedOrSynthesised: j['observed_or_synthesised'] ?? 'synthesised',
      );
}

class PriceBand {
  final double pointInr;
  final double bandLowInr;
  final double bandHighInr;
  final String confidence;
  final String confidenceReason;
  final double seasonalMultiplier;
  final List<Comparable> comparables;

  PriceBand({
    required this.pointInr,
    required this.bandLowInr,
    required this.bandHighInr,
    required this.confidence,
    required this.confidenceReason,
    required this.seasonalMultiplier,
    required this.comparables,
  });

  factory PriceBand.fromJson(Map<String, dynamic> j) => PriceBand(
        pointInr: (j['point_inr'] as num?)?.toDouble() ?? 0,
        bandLowInr: (j['band_low_inr'] as num?)?.toDouble() ?? 0,
        bandHighInr: (j['band_high_inr'] as num?)?.toDouble() ?? 0,
        confidence: j['confidence'] ?? 'low',
        confidenceReason: j['confidence_reason'] ?? '',
        seasonalMultiplier: (j['seasonal_multiplier'] as num?)?.toDouble() ?? 1.0,
        comparables: (j['comparables'] as List<dynamic>? ?? [])
            .map((e) => Comparable.fromJson(e))
            .toList(),
      );
}

class PriceSuggestion {
  final double valueInr;
  final String basedOn;
  final String note;

  PriceSuggestion({required this.valueInr, required this.basedOn, required this.note});

  factory PriceSuggestion.fromJson(Map<String, dynamic> j) => PriceSuggestion(
        valueInr: (j['value_inr'] as num?)?.toDouble() ?? 0,
        basedOn: j['based_on'] ?? 'model',
        note: j['note'] ?? '',
      );
}

class ThreeBars {
  final double materialInr;
  final double demandInr;
  final double regionInr;

  ThreeBars({required this.materialInr, required this.demandInr, required this.regionInr});

  factory ThreeBars.fromJson(Map<String, dynamic> j) => ThreeBars(
        materialInr: (j['material_inr'] as num?)?.toDouble() ?? 0,
        demandInr: (j['demand_inr'] as num?)?.toDouble() ?? 0,
        regionInr: (j['region_inr'] as num?)?.toDouble() ?? 0,
      );
}

class Quote {
  final FloorResult floor;
  final PriceBand band;
  final PriceSuggestion suggested;
  final ThreeBars explain;

  Quote({required this.floor, required this.band, required this.suggested, required this.explain});

  factory Quote.fromJson(Map<String, dynamic> j) => Quote(
        floor: FloorResult.fromJson(j['floor']),
        band: PriceBand.fromJson(j['band']),
        suggested: PriceSuggestion.fromJson(j['suggested']),
        explain: ThreeBars.fromJson(j['explain']),
      );
}
