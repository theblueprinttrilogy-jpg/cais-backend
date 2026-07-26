using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;

namespace RevitAudit.Engine
{
    /// <summary>
    /// Provides high-precision, deterministic unit conversions for the Revit audit system.
    /// All conversions are relative to Universal Base Units (UBU) defined for each physical magnitude.
    /// This implementation supports all units commonly used in general construction.
    /// </summary>
    /// <remarks>
    /// <para><b>Universal Base Units (UBU):</b></para>
    /// <list type="bullet">
    /// <item><description>Length: Millimeter (mm) - Revit's native internal unit</description></item>
    /// <item><description>Area: Square Meter (m²) - Standard for construction takeoffs</description></item>
    /// <item><description>Volume: Cubic Meter (m³) - Foundation for concrete, earthwork</description></item>
    /// <item><description>Liquid Volume: Liter (L) - Plumbing, HVAC, fire suppression</description></item>
    /// <item><description>Mass: Kilogram (kg) - Structural loads, material orders</description></item>
    /// <item><description>Temperature: Kelvin (K) - Thermodynamic calculations</description></item>
    /// <item><description>Power: Watt (W) - HVAC, electrical loads</description></item>
    /// <item><description>Pressure: Pascal (Pa) - Structural engineering, HVAC</description></item>
    /// </list>
    /// </remarks>
    public static class UniversalConverter
    {
        #region Private Static Fields

        private static readonly Lazy<ReadOnlyDictionary<string, double>> _lengthFactors;
        private static readonly Lazy<ReadOnlyDictionary<string, double>> _areaFactors;
        private static readonly Lazy<ReadOnlyDictionary<string, double>> _volumeFactors;
        private static readonly Lazy<ReadOnlyDictionary<string, double>> _liquidVolumeFactors;
        private static readonly Lazy<ReadOnlyDictionary<string, double>> _massFactors;
        private static readonly Lazy<ReadOnlyDictionary<string, double>> _powerFactors;
        private static readonly Lazy<ReadOnlyDictionary<string, double>> _pressureFactors;

        #endregion

        #region Static Constructor

        /// <summary>
        /// Static constructor initializes all conversion matrices with NIST-traceable values.
        /// Uses lazy initialization for thread-safe, one-time construction.
        /// </summary>
        static UniversalConverter()
        {
            #region Length Factors (UBU: Millimeter - mm)

            _lengthFactors = new Lazy<ReadOnlyDictionary<string, double>>(() =>
                new ReadOnlyDictionary<string, double>(new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase)
                {
                    // Metric Units
                    { "mm", 1.0 },
                    { "cm", 10.0 },
                    { "dm", 100.0 },
                    { "m", 1000.0 },
                    { "km", 1000000.0 },
                    
                    // Imperial/US Units
                    { "in", 25.4 },
                    { "ft", 304.8 },
                    { "yd", 914.4 },
                    { "mi", 1609344.0 },
                    
                    // Surveyor's Units
                    { "chain", 201168.0 },        // 66 feet
                    { "link", 201.168 },           // 1/100 chain
                    { "rod", 5029.2 },             // 16.5 feet
                    { "fathom", 1828.8 },          // 6 feet
                    { "cable", 185200.0 },         // 607.61 feet (international)
                    { "nautical_mile", 1852000.0 }, // 1,852,000 mm
                    
                    // Typographic/Architectural
                    { "pt", 0.352778 },            // Point (1/72 inch)
                    { "pica", 4.23333 },           // Pica (12 points)
                    { "architectural_ft", 304.8 },  // Architectural foot (same as survey ft)
                    
                    // Fractions (common construction fractions in inches)
                    { "1_8_in", 3.175 },            // 1/8 inch
                    { "1_4_in", 6.35 },             // 1/4 inch
                    { "3_8_in", 9.525 },            // 3/8 inch
                    { "1_2_in", 12.7 },             // 1/2 inch
                    { "5_8_in", 15.875 },           // 5/8 inch
                    { "3_4_in", 19.05 },            // 3/4 inch
                    { "7_8_in", 22.225 }            // 7/8 inch
                }));

            #endregion

            #region Area Factors (UBU: Square Meter - m²)

            _areaFactors = new Lazy<ReadOnlyDictionary<string, double>>(() =>
                new ReadOnlyDictionary<string, double>(new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase)
                {
                    // Metric Units
                    { "m2", 1.0 },
                    { "sq_mm", 0.000001 },
                    { "sq_cm", 0.0001 },
                    { "sq_dm", 0.01 },
                    { "sq_km", 1000000.0 },
                    
                    // Imperial/US Units
                    { "sq_in", 0.00064516 },
                    { "sq_ft", 0.09290304 },
                    { "sq_yd", 0.83612736 },
                    { "sq_mi", 2589988.110336 },
                    
                    // Land Measurement
                    { "acres", 4046.8564224 },
                    { "hectares", 10000.0 },
                    { "sq_rod", 25.29285264 },      // 1 rod = 16.5 ft, sq_rod = 272.25 sq_ft
                    { "sq_chain", 404.68564224 },    // 1 chain = 66 ft, sq_chain = 4356 sq_ft
                    { "sq_link", 0.040468564224 },   // 1/100 chain squared
                    
                    // Construction/Takeoff Units
                    { "board_ft", 0.002359737216 },  // 1 board foot = 144 cu_in (as area for lumber)
                    { "roofing_square", 9.290304 },  // 100 sq_ft = 1 roofing square
                    { "square_footage", 0.09290304 }, // Alias for sq_ft
                    
                    // Fractional Inch Squares (common in construction)
                    { "sq_1_4_in", 0.00004032256 },  // (1/4 inch)^2
                    { "sq_1_2_in", 0.00016129 },     // (1/2 inch)^2
                    { "sq_3_4_in", 0.0003629025 }    // (3/4 inch)^2
                }));

            #endregion

            #region Volume Factors (UBU: Cubic Meter - m³)

            _volumeFactors = new Lazy<ReadOnlyDictionary<string, double>>(() =>
                new ReadOnlyDictionary<string, double>(new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase)
                {
                    // Metric Units
                    { "m3", 1.0 },
                    { "cu_mm", 1e-9 },
                    { "cu_cm", 0.000001 },
                    { "cu_dm", 0.001 },              // 1 liter = 1 cu_dm
                    { "cu_km", 1000000000.0 },
                    
                    // Imperial/US Cubic Units
                    { "cu_in", 0.000016387064 },
                    { "cu_ft", 0.028316846592 },
                    { "cu_yd", 0.764554857984 },
                    { "cu_mi", 4168181825.44058 },
                    
                    // Construction Aggregate Units
                    { "board_ft", 0.002359737216 },  // 1 board foot = 144 cu_in
                    { "cubic_foot_bulk", 0.028316846592 }, // Alias for cu_ft
                    
                    // Earthwork/Excavation
                    { "cubic_yard_bulk", 0.764554857984 }, // Alias for cu_yd
                    { "cubic_yard_compacted", 0.764554857984 }, // Same measurement, contextual
                    
                    // Timber/Logging Units
                    { "hundred_cu_ft", 2.8316846592 }, // 100 cu_ft (CCF)
                    { "thousand_board_ft", 2.359737216 }, // 1000 board feet (MBF)
                    
                    // Fractional Cubic Inches (common for small parts)
                    { "cu_1_4_in", 0.0000010241915 }, // (1/4 inch)^3
                    { "cu_1_2_in", 0.000008193532 },  // (1/2 inch)^3
                    { "cu_3_4_in", 0.000027648 }      // (3/4 inch)^3
                }));

            #endregion

            #region Liquid Volume Factors (UBU: Liter - L)

            _liquidVolumeFactors = new Lazy<ReadOnlyDictionary<string, double>>(() =>
                new ReadOnlyDictionary<string, double>(new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase)
                {
                    // Metric Units
                    { "L", 1.0 },
                    { "ml", 0.001 },
                    { "cl", 0.01 },
                    { "dl", 0.1 },
                    { "hL", 100.0 },
                    { "kL", 1000.0 },
                    { "cu_meter", 1000.0 },          // 1 m³ = 1000 L
                    
                    // US Liquid Units
                    { "us_gal", 3.785411784 },
                    { "us_qt", 0.946352946 },
                    { "us_pt", 0.473176473 },
                    { "us_cup", 0.2365882365 },
                    { "us_fl_oz", 0.0295735295625 },
                    { "us_tbsp", 0.01478676478125 },
                    { "us_tsp", 0.00492892159375 },
                    
                    // Imperial (UK) Liquid Units
                    { "uk_gal", 4.54609 },
                    { "uk_qt", 1.1365225 },
                    { "uk_pt", 0.56826125 },
                    { "uk_fl_oz", 0.0284130625 },
                    
                    // Construction Fluid Units
                    { "barrel_us", 158.987294928 },  // US oil barrel
                    { "barrel_uk", 163.65924 },      // UK imperial barrel
                    { "cfm", 28.316846592 },          // Cubic foot per minute (L/min equivalent)
                    { "gpm", 3.785411784 },           // US gallons per minute (L/min equivalent)
                    
                    // HVAC/Plumbing
                    { "btu_lb", 2326.0 },             // BTU per pound (specific energy, approximate)
                    
                    // Fire Suppression
                    { "us_gal_water", 3.785411784 }   // Same as us_gal, contextual
                }));

            #endregion

            #region Mass/Weight Factors (UBU: Kilogram - kg)

            _massFactors = new Lazy<ReadOnlyDictionary<string, double>>(() =>
                new ReadOnlyDictionary<string, double>(new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase)
                {
                    // Metric Units
                    { "kg", 1.0 },
                    { "g", 0.001 },
                    { "mg", 0.000001 },
                    { "tonne", 1000.0 },              // Metric ton
                    { "quintal", 100.0 },             // Metric quintal
                    
                    // Imperial/US Units
                    { "lb", 0.45359237 },
                    { "oz", 0.028349523125 },
                    { "st", 6.35029318 },             // Stone (14 lbs)
                    { "us_ton", 907.18474 },          // Short ton (2000 lbs)
                    { "uk_ton", 1016.0469088 },       // Long ton (2240 lbs)
                    
                    // Construction Material Units
                    { "tonne_metric", 1000.0 },       // Alias for tonne
                    { "ton_short", 907.18474 },       // Alias for us_ton
                    { "ton_long", 1016.0469088 },     // Alias for uk_ton
                    
                    // Structural Steel
                    { "kips", 453.59237 },             // 1000 lbs (kip)
                    { "kip_ft", 453.59237 },           // kip per foot (linear weight)
                    
                    // Concrete/Aggregate (specific weights by volume)
                    { "lb_cu_ft", 16.018463374 },      // Density conversion
                    { "kg_cu_m", 1.0 },                // kg/m³ (density base)
                    
                    // Fractional Ounces (precious/small materials)
                    { "oz_troy", 0.0311034768 },       // Troy ounce
                    { "dwt", 0.00155517384 },          // Pennyweight (1/20 troy oz)
                    { "grain", 0.00006479891 }         // Grain (1/7000 lb)
                }));

            #endregion

            #region Power/Energy Factors (UBU: Watt - W)

            _powerFactors = new Lazy<ReadOnlyDictionary<string, double>>(() =>
                new ReadOnlyDictionary<string, double>(new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase)
                {
                    // Metric Units
                    { "W", 1.0 },
                    { "kW", 1000.0 },
                    { "MW", 1000000.0 },
                    { "GW", 1000000000.0 },
                    
                    // Thermal/HVAC Units
                    { "BTU_h", 0.2930710701722222 },  // BTU per hour
                    { "BTU_min", 17.5842642103333 },  // BTU per minute
                    { "BTU_s", 1055.05585262 },       // BTU per second
                    { "ton_refrigeration", 3516.8528420667 }, // 1 ton = 12,000 BTU/h
                    { "hp_metric", 735.49875 },        // Metric horsepower
                    { "hp_imperial", 745.69987158227022 }, // Imperial/US horsepower
                    { "hp_boiler", 9809.5 },          // Boiler horsepower
                    { "calorie_s", 4.1868 },           // Calorie per second
                    { "kcal_h", 1.163 },               // Kilocalorie per hour
                    
                    // Electrical Units
                    { "VA", 1.0 },                     // Volt-Ampere (Apparent Power)
                    { "kVA", 1000.0 },
                    { "MVA", 1000000.0 },
                    
                    // Lighting
                    { "lumen", 0.001464128843338 },    // Lumen to watt (typical conversion)
                    { "lux", 0.001464128843338 },      // Lux (lumens/m²) approximated
                    
                    // Energy (Work) Units
                    { "J_s", 1.0 },                    // Joule per second = Watt
                    { "kWh", 3600000.0 },              // Kilowatt-hour (energy)
                    { "BTU", 1055.05585262 },          // BTU (energy, not power)
                    { "therm", 105505585.262 },        // 100,000 BTU
                    { "quad", 1055055852620000.0 }     // Quadrillion BTU
                }));

            #endregion

            #region Pressure/Stress Factors (UBU: Pascal - Pa)

            _pressureFactors = new Lazy<ReadOnlyDictionary<string, double>>(() =>
                new ReadOnlyDictionary<string, double>(new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase)
                {
                    // Metric Units
                    { "Pa", 1.0 },
                    { "kPa", 1000.0 },
                    { "MPa", 1000000.0 },
                    { "GPa", 1000000000.0 },
                    { "bar", 100000.0 },
                    { "mbar", 100.0 },
                    
                    // Imperial/US Units
                    { "psi", 6894.757293168361 },
                    { "ksi", 6894757.293168361 },     // 1000 psi
                    { "psf", 47.88025898033585 },
                    { "psia", 6894.757293168361 },    // PSI absolute
                    { "psig", 6894.757293168361 },    // PSI gauge (same factor, contextual)
                    
                    // Structural Engineering
                    { "psf_live", 47.88025898033585 }, // Pounds per square foot (live load)
                    { "psf_dead", 47.88025898033585 }, // Pounds per square foot (dead load)
                    { "kips_sq_ft", 47880.25898033585 }, // Kips per square foot
                    
                    // Fluid/HVAC Pressure
                    { "in_Hg", 3386.388640341 }       // Inches of mercury
                }));

            #endregion
        }

        #endregion

        #region Public Accessors

        /// <summary>
        /// Gets the immutable read-only dictionary containing length conversion factors.
        /// Factor represents: [1 unit] = [Factor] Millimeters (mm).
        /// </summary>
        public static ReadOnlyDictionary<string, double> LengthFactors => _lengthFactors.Value;

        /// <summary>
        /// Gets the immutable read-only dictionary containing area conversion factors.
        /// Factor represents: [1 unit] = [Factor] Square Meters (m²).
        /// </summary>
        public static ReadOnlyDictionary<string, double> AreaFactors => _areaFactors.Value;

        /// <summary>
        /// Gets the immutable read-only dictionary containing volume conversion factors.
        /// Factor represents: [1 unit] = [Factor] Cubic Meters (m³).
        /// </summary>
        public static ReadOnlyDictionary<string, double> VolumeFactors => _volumeFactors.Value;

        /// <summary>
        /// Gets the immutable read-only dictionary containing liquid volume conversion factors.
        /// Factor represents: [1 unit] = [Factor] Liters (L).
        /// </summary>
        public static ReadOnlyDictionary<string, double> LiquidVolumeFactors => _liquidVolumeFactors.Value;

        /// <summary>
        /// Gets the immutable read-only dictionary containing mass conversion factors.
        /// Factor represents: [1 unit] = [Factor] Kilograms (kg).
        /// </summary>
        public static ReadOnlyDictionary<string, double> MassFactors => _massFactors.Value;

        /// <summary>
        /// Gets the immutable read-only dictionary containing power conversion factors.
        /// Factor represents: [1 unit] = [Factor] Watts (W).
        /// </summary>
        public static ReadOnlyDictionary<string, double> PowerFactors => _powerFactors.Value;

        /// <summary>
        /// Gets the immutable read-only dictionary containing pressure conversion factors.
        /// Factor represents: [1 unit] = [Factor] Pascals (Pa).
        /// </summary>
        public static ReadOnlyDictionary<string, double> PressureFactors => _pressureFactors.Value;

        #endregion

        #region Length Conversion Methods

        /// <summary>
        /// Converts a given length value from the specified source unit to the Universal Base Unit (Millimeters).
        /// </summary>
        /// <param name="value">The numeric value in the source unit to convert.</param>
        /// <param name="unitKey">The case-insensitive unit key (e.g., "ft", "m", "in").</param>
        /// <returns>The equivalent length in millimeters (mm).</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided unitKey does not exist in the Length dictionary.</exception>
        /// <remarks>Formula: <c>result = value * LengthFactors[unitKey]</c></remarks>
        public static double LengthToBase(double value, string unitKey)
        {
            if (!LengthFactors.TryGetValue(unitKey, out double factor))
                throw new KeyNotFoundException($"Length unit '{unitKey}' is not defined in the conversion matrix.");

            return value * factor;
        }

        /// <summary>
        /// Converts a length value from the Universal Base Unit (Millimeters) to the specified target unit.
        /// </summary>
        /// <param name="value">The numeric value in millimeters (mm).</param>
        /// <param name="targetUnitKey">The case-insensitive target unit key (e.g., "ft", "m", "in").</param>
        /// <returns>The equivalent length in the specified target unit.</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided targetUnitKey does not exist in the Length dictionary.</exception>
        /// <remarks>Formula: <c>result = value / LengthFactors[targetUnitKey]</c></remarks>
        public static double LengthFromBase(double value, string targetUnitKey)
        {
            if (!LengthFactors.TryGetValue(targetUnitKey, out double factor))
                throw new KeyNotFoundException($"Length unit '{targetUnitKey}' is not defined in the conversion matrix.");

            return value / factor;
        }

        #endregion

        #region Area Conversion Methods

        /// <summary>
        /// Converts a given area value from the specified source unit to the Universal Base Unit (Square Meters).
        /// </summary>
        /// <param name="value">The numeric value in the source unit to convert.</param>
        /// <param name="unitKey">The case-insensitive unit key (e.g., "sq_ft", "m2", "acres").</param>
        /// <returns>The equivalent area in square meters (m²).</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided unitKey does not exist in the Area dictionary.</exception>
        /// <remarks>Formula: <c>result = value * AreaFactors[unitKey]</c></remarks>
        public static double AreaToBase(double value, string unitKey)
        {
            if (!AreaFactors.TryGetValue(unitKey, out double factor))
                throw new KeyNotFoundException($"Area unit '{unitKey}' is not defined in the conversion matrix.");

            return value * factor;
        }

        /// <summary>
        /// Converts an area value from the Universal Base Unit (Square Meters) to the specified target unit.
        /// </summary>
        /// <param name="value">The numeric value in square meters (m²).</param>
        /// <param name="targetUnitKey">The case-insensitive target unit key (e.g., "sq_ft", "m2", "acres").</param>
        /// <returns>The equivalent area in the specified target unit.</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided targetUnitKey does not exist in the Area dictionary.</exception>
        /// <remarks>Formula: <c>result = value / AreaFactors[targetUnitKey]</c></remarks>
        public static double AreaFromBase(double value, string targetUnitKey)
        {
            if (!AreaFactors.TryGetValue(targetUnitKey, out double factor))
                throw new KeyNotFoundException($"Area unit '{targetUnitKey}' is not defined in the conversion matrix.");

            return value / factor;
        }

        #endregion

        #region Volume Conversion Methods

        /// <summary>
        /// Converts a given volume value from the specified source unit to the Universal Base Unit (Cubic Meters).
        /// </summary>
        /// <param name="value">The numeric value in the source unit to convert.</param>
        /// <param name="unitKey">The case-insensitive unit key (e.g., "cu_ft", "m3", "board_ft").</param>
        /// <returns>The equivalent volume in cubic meters (m³).</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided unitKey does not exist in the Volume dictionary.</exception>
        /// <remarks>Formula: <c>result = value * VolumeFactors[unitKey]</c></remarks>
        public static double VolumeToBase(double value, string unitKey)
        {
            if (!VolumeFactors.TryGetValue(unitKey, out double factor))
                throw new KeyNotFoundException($"Volume unit '{unitKey}' is not defined in the conversion matrix.");

            return value * factor;
        }

        /// <summary>
        /// Converts a volume value from the Universal Base Unit (Cubic Meters) to the specified target unit.
        /// </summary>
        /// <param name="value">The numeric value in cubic meters (m³).</param>
        /// <param name="targetUnitKey">The case-insensitive target unit key (e.g., "cu_ft", "m3", "board_ft").</param>
        /// <returns>The equivalent volume in the specified target unit.</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided targetUnitKey does not exist in the Volume dictionary.</exception>
        /// <remarks>Formula: <c>result = value / VolumeFactors[targetUnitKey]</c></remarks>
        public static double VolumeFromBase(double value, string targetUnitKey)
        {
            if (!VolumeFactors.TryGetValue(targetUnitKey, out double factor))
                throw new KeyNotFoundException($"Volume unit '{targetUnitKey}' is not defined in the conversion matrix.");

            return value / factor;
        }

        #endregion

        #region Liquid Volume Conversion Methods

        /// <summary>
        /// Converts a given liquid volume value from the specified source unit to the Universal Base Unit (Liters).
        /// </summary>
        /// <param name="value">The numeric value in the source unit to convert.</param>
        /// <param name="unitKey">The case-insensitive unit key (e.g., "us_gal", "L", "uk_pt").</param>
        /// <returns>The equivalent volume in liters (L).</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided unitKey does not exist in the LiquidVolume dictionary.</exception>
        /// <remarks>Formula: <c>result = value * LiquidVolumeFactors[unitKey]</c></remarks>
        public static double LiquidVolumeToBase(double value, string unitKey)
        {
            if (!LiquidVolumeFactors.TryGetValue(unitKey, out double factor))
                throw new KeyNotFoundException($"Liquid volume unit '{unitKey}' is not defined in the conversion matrix.");

            return value * factor;
        }

        /// <summary>
        /// Converts a liquid volume value from the Universal Base Unit (Liters) to the specified target unit.
        /// </summary>
        /// <param name="value">The numeric value in liters (L).</param>
        /// <param name="targetUnitKey">The case-insensitive target unit key (e.g., "us_gal", "L", "uk_pt").</param>
        /// <returns>The equivalent volume in the specified target unit.</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided targetUnitKey does not exist in the LiquidVolume dictionary.</exception>
        /// <remarks>Formula: <c>result = value / LiquidVolumeFactors[targetUnitKey]</c></remarks>
        public static double LiquidVolumeFromBase(double value, string targetUnitKey)
        {
            if (!LiquidVolumeFactors.TryGetValue(targetUnitKey, out double factor))
                throw new KeyNotFoundException($"Liquid volume unit '{targetUnitKey}' is not defined in the conversion matrix.");

            return value / factor;
        }

        #endregion

        #region Mass/Weight Conversion Methods

        /// <summary>
        /// Converts a given mass value from the specified source unit to the Universal Base Unit (Kilograms).
        /// </summary>
        /// <param name="value">The numeric value in the source unit to convert.</param>
        /// <param name="unitKey">The case-insensitive unit key (e.g., "lb", "kg", "tonne").</param>
        /// <returns>The equivalent mass in kilograms (kg).</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided unitKey does not exist in the Mass dictionary.</exception>
        /// <remarks>Formula: <c>result = value * MassFactors[unitKey]</c></remarks>
        public static double MassToBase(double value, string unitKey)
        {
            if (!MassFactors.TryGetValue(unitKey, out double factor))
                throw new KeyNotFoundException($"Mass unit '{unitKey}' is not defined in the conversion matrix.");

            return value * factor;
        }

        /// <summary>
        /// Converts a mass value from the Universal Base Unit (Kilograms) to the specified target unit.
        /// </summary>
        /// <param name="value">The numeric value in kilograms (kg).</param>
        /// <param name="targetUnitKey">The case-insensitive target unit key (e.g., "lb", "kg", "tonne").</param>
        /// <returns>The equivalent mass in the specified target unit.</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided targetUnitKey does not exist in the Mass dictionary.</exception>
        /// <remarks>Formula: <c>result = value / MassFactors[targetUnitKey]</c></remarks>
        public static double MassFromBase(double value, string targetUnitKey)
        {
            if (!MassFactors.TryGetValue(targetUnitKey, out double factor))
                throw new KeyNotFoundException($"Mass unit '{targetUnitKey}' is not defined in the conversion matrix.");

            return value / factor;
        }

        #endregion

        #region Power/Energy Conversion Methods

        /// <summary>
        /// Converts a given power value from the specified source unit to the Universal Base Unit (Watts).
        /// </summary>
        /// <param name="value">The numeric value in the source unit to convert.</param>
        /// <param name="unitKey">The case-insensitive unit key (e.g., "BTU_h", "kW", "hp_imperial").</param>
        /// <returns>The equivalent power in watts (W).</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided unitKey does not exist in the Power dictionary.</exception>
        /// <remarks>Formula: <c>result = value * PowerFactors[unitKey]</c></remarks>
        public static double PowerToBase(double value, string unitKey)
        {
            if (!PowerFactors.TryGetValue(unitKey, out double factor))
                throw new KeyNotFoundException($"Power unit '{unitKey}' is not defined in the conversion matrix.");

            return value * factor;
        }

        /// <summary>
        /// Converts a power value from the Universal Base Unit (Watts) to the specified target unit.
        /// </summary>
        /// <param name="value">The numeric value in watts (W).</param>
        /// <param name="targetUnitKey">The case-insensitive target unit key (e.g., "BTU_h", "kW", "hp_imperial").</param>
        /// <returns>The equivalent power in the specified target unit.</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided targetUnitKey does not exist in the Power dictionary.</exception>
        /// <remarks>Formula: <c>result = value / PowerFactors[targetUnitKey]</c></remarks>
        public static double PowerFromBase(double value, string targetUnitKey)
        {
            if (!PowerFactors.TryGetValue(targetUnitKey, out double factor))
                throw new KeyNotFoundException($"Power unit '{targetUnitKey}' is not defined in the conversion matrix.");

            return value / factor;
        }

        #endregion

        #region Pressure/Stress Conversion Methods

        /// <summary>
        /// Converts a given pressure value from the specified source unit to the Universal Base Unit (Pascals).
        /// </summary>
        /// <param name="value">The numeric value in the source unit to convert.</param>
        /// <param name="unitKey">The case-insensitive unit key (e.g., "psi", "kPa", "bar").</param>
        /// <returns>The equivalent pressure in pascals (Pa).</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided unitKey does not exist in the Pressure dictionary.</exception>
        /// <remarks>Formula: <c>result = value * PressureFactors[unitKey]</c></remarks>
        public static double PressureToBase(double value, string unitKey)
        {
            if (!PressureFactors.TryGetValue(unitKey, out double factor))
                throw new KeyNotFoundException($"Pressure unit '{unitKey}' is not defined in the conversion matrix.");

            return value * factor;
        }

        /// <summary>
        /// Converts a pressure value from the Universal Base Unit (Pascals) to the specified target unit.
        /// </summary>
        /// <param name="value">The numeric value in pascals (Pa).</param>
        /// <param name="targetUnitKey">The case-insensitive target unit key (e.g., "psi", "kPa", "bar").</param>
        /// <returns>The equivalent pressure in the specified target unit.</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided targetUnitKey does not exist in the Pressure dictionary.</exception>
        /// <remarks>Formula: <c>result = value / PressureFactors[targetUnitKey]</c></remarks>
        public static double PressureFromBase(double value, string targetUnitKey)
        {
            if (!PressureFactors.TryGetValue(targetUnitKey, out double factor))
                throw new KeyNotFoundException($"Pressure unit '{targetUnitKey}' is not defined in the conversion matrix.");

            return value / factor;
        }

        #endregion

        #region Temperature Conversion Method

        /// <summary>
        /// Converts a temperature value between any two supported units (Kelvin, Celsius, Fahrenheit).
        /// This method uses decimal arithmetic for offset handling to guarantee deterministic,
        /// high-precision results for standard benchmark values (e.g., 0°C = 273.15K).
        /// </summary>
        /// <param name="value">The numeric temperature value to convert.</param>
        /// <param name="fromUnit">The case-insensitive source unit key ("K", "C", or "F").</param>
        /// <param name="toUnit">The case-insensitive target unit key ("K", "C", or "F").</param>
        /// <returns>The equivalent temperature in the target unit.</returns>
        /// <exception cref="KeyNotFoundException">Thrown when the provided unit key is not "K", "C", or "F".</exception>
        /// <remarks>
        /// Formulas used internally (all offsets handled in Decimal for precision):
        /// <list type="bullet">
        /// <item><description>Kelvin: <c>K = C + 273.15</c></description></item>
        /// <item><description>Celsius: <c>C = K - 273.15</c></description></item>
        /// <item><description>Fahrenheit: <c>F = (C × 9/5) + 32</c></description></item>
        /// <item><description>Kelvin to Fahrenheit: <c>F = ((K - 273.15) × 9/5) + 32</c></description></item>
        /// </list>
        /// </remarks>
        public static double ConvertTemperature(double value, string fromUnit, string toUnit)
        {
            string from = fromUnit.ToUpperInvariant();
            string to = toUnit.ToUpperInvariant();

            if (from == to)
                return value;

            string[] validUnits = { "K", "C", "F" };
            if (!validUnits.Contains(from))
                throw new KeyNotFoundException($"Temperature source unit '{fromUnit}' is not supported. Use K, C, or F.");
            if (!validUnits.Contains(to))
                throw new KeyNotFoundException($"Temperature target unit '{toUnit}' is not supported. Use K, C, or F.");

            decimal input = (decimal)value;
            decimal kelvin;

            switch (from)
            {
                case "K":
                    kelvin = input;
                    break;
                case "C":
                    kelvin = input + 273.15m;
                    break;
                case "F":
                    kelvin = ((input - 32m) * 5m / 9m) + 273.15m;
                    break;
                default:
                    throw new KeyNotFoundException($"Unhandled temperature unit: {fromUnit}");
            }

            decimal result;
            switch (to)
            {
                case "K":
                    result = kelvin;
                    break;
                case "C":
                    result = kelvin - 273.15m;
                    break;
                case "F":
                    result = ((kelvin - 273.15m) * 9m / 5m) + 32m;
                    break;
                default:
                    throw new KeyNotFoundException($"Unhandled temperature unit: {toUnit}");
            }

            return (double)result;
        }

        #endregion

        #region Utility Methods

        /// <summary>
        /// Validates if a given unit key exists in any of the conversion dictionaries.
        /// </summary>
        /// <param name="unitKey">The case-insensitive unit key to validate.</param>
        /// <param name="magnitude">When this method returns, contains the magnitude where the unit was found, or null.</param>
        /// <returns>True if the unit exists in any dictionary; otherwise, false.</returns>
        public static bool IsValidUnit(string unitKey, out string magnitude)
        {
            magnitude = null;
            
            if (LengthFactors.ContainsKey(unitKey)) { magnitude = "Length"; return true; }
            if (AreaFactors.ContainsKey(unitKey)) { magnitude = "Area"; return true; }
            if (VolumeFactors.ContainsKey(unitKey)) { magnitude = "Volume"; return true; }
            if (LiquidVolumeFactors.ContainsKey(unitKey)) { magnitude = "LiquidVolume"; return true; }
            if (MassFactors.ContainsKey(unitKey)) { magnitude = "Mass"; return true; }
            if (PowerFactors.ContainsKey(unitKey)) { magnitude = "Power"; return true; }
            if (PressureFactors.ContainsKey(unitKey)) { magnitude = "Pressure"; return true; }
            
            return false;
        }

        /// <summary>
        /// Gets all available unit keys across all magnitudes.
        /// </summary>
        /// <returns>An array containing all unit keys from all conversion dictionaries.</returns>
        public static string[] GetAllUnitKeys()
        {
            var allKeys = new List<string>();
            allKeys.AddRange(LengthFactors.Keys);
            allKeys.AddRange(AreaFactors.Keys);
            allKeys.AddRange(VolumeFactors.Keys);
            allKeys.AddRange(LiquidVolumeFactors.Keys);
            allKeys.AddRange(MassFactors.Keys);
            allKeys.AddRange(PowerFactors.Keys);
            allKeys.AddRange(PressureFactors.Keys);
            
            return allKeys.Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        }

        #endregion
    }
}
